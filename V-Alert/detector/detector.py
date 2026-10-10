"""Detector de alertas tempranas para gracko.

Revisa metricas.csv y logs.md y muestra en la terminal los avisos de incidencia
detectados y los senuelos que se descartaron. Los horarios, el respaldo y los
eventos del negocio se leen de contexto.md (no hay fechas fijas en el código).

Uso:
    python detector/detector.py                               # toda la semana
    python detector/detector.py --azar                        # FILAS minutos al azar
    python detector/detector.py --inicio "2026-10-10 20:00"   # FILAS minutos desde esa hora
    python detector/detector.py --carpeta data/corridas/corrida_05/gracko
    python detector/detector.py --discord                     # además envía los avisos a Discord
    python detector/detector.py --salida alertas.csv          # guarda la entrega en un CSV
    python detector/detector.py --gemini                      # explica cada alerta en lenguaje sencillo
"""
import argparse
import csv
import random
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

from discord import enviar_a_discord
from gemini import describir_alertas

CARPETA = Path(__file__).resolve().parent.parent / "data" / "gracko"
FILAS = 9200

# --- Reglas del negocio (puedes ajustar estos números) ---
CPU_LIMITE = 40              # % de CPU
DISCO_MIN, DISCO_MAX = 60, 70  # % de disco en /data
VPN_MIN, VPN_MAX = 13, 100000  # intentos fallidos (más de 12 = ataque)
VPN_VENTANA_MIN = 35         # minutos
ERRORES_LIMITE = 0.5         # errores por minuto (promedio 1 h); lo normal es ~0.2
CPU_PICO_MAX = 45            # si hubo picos de CPU, los errores son de otro problema
MADRUGADA = (0, 6)           # de 00:00 a 05:59
HORAS_MISMO_INCIDENTE = 12   # si el problema desaparece más de 12 h, es un incidente nuevo
RESPALDO_MIN = 45            # el respaldo dura ~40 min (+5: el promedio de CPU tarda en bajar)
CONFIANZA_MAX = 0.99         # nunca decimos 100 %

# Si contexto.md no trae algún dato, se usan estos valores
HORARIO_DEFECTO = {0: (8, 18), 1: (8, 18), 2: (8, 18), 3: (8, 18), 4: (8, 18), 5: (9, 13)}
RESPALDO_HORA_DEFECTO = (23, 0)

DIAS = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "domingo": 6}
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
RANGO_HORAS = r"(\d{1,2}):(\d{2})\s*[–-]\s*(\d{1,2}):(\d{2})"


# ---------------------------------------------------------------------------
# Contexto del negocio (contexto.md)
# ---------------------------------------------------------------------------

def sin_acentos(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def dia_de_semana(palabra):
    palabra = sin_acentos(palabra)
    return DIAS.get(palabra, DIAS.get(palabra.rstrip("s")))  # "sabados" -> "sabado"


def leer_horario(texto):
    """'lunes a viernes 08:00–18:00; sabados 09:00–13:00' -> {dia: (hora_ini, hora_fin)}"""
    horario = {}
    for parte in texto.split(";"):
        m = re.search(r"([a-záéíóú]+)(?:\s+a\s+([a-záéíóú]+))?\s+" + RANGO_HORAS, parte.lower())
        if not m:
            continue
        desde = dia_de_semana(m.group(1))
        hasta = dia_de_semana(m.group(2)) if m.group(2) else desde
        if desde is None or hasta is None:
            continue
        for dia in range(desde, hasta + 1):
            horario[dia] = (int(m.group(3)), int(m.group(5)))
    return horario


def leer_contexto(carpeta, anio):
    """Lee horario de oficina, hora del respaldo y eventos de negocio de contexto.md."""
    ctx = {"horario": HORARIO_DEFECTO, "respaldo": RESPALDO_HORA_DEFECTO, "eventos": []}
    archivo = Path(carpeta) / "contexto.md"
    if not archivo.exists():
        print(f"⚠️  No encontré {archivo}; uso horario y respaldo por defecto.")
        return ctx

    en_eventos = False
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            en_eventos = "evento" in sin_acentos(linea)
            continue

        if "**Horario:**" in linea:
            horario = leer_horario(linea.split("**Horario:**", 1)[1])
            if horario:
                ctx["horario"] = horario

        elif "respaldo" in linea.lower() and "|" in linea:
            m = re.search(r"(\d{1,2}):(\d{2})", linea)
            if m:
                ctx["respaldo"] = (int(m.group(1)), int(m.group(2)))

        elif en_eventos and linea.startswith("- "):
            # - **Viernes 9 de octubre:** carga masiva de declaraciones ... (17:00–19:30).
            fecha = re.search(r"(\d{1,2}) de ([a-záéíóú]+)", linea.lower())
            horas = re.search(RANGO_HORAS, linea)
            if not (fecha and horas) or sin_acentos(fecha.group(2)) not in MESES:
                continue
            dia = pd.Timestamp(anio, MESES[sin_acentos(fecha.group(2))], int(fecha.group(1)))
            inicio = dia + pd.Timedelta(hours=int(horas.group(1)), minutes=int(horas.group(2)))
            fin = dia + pd.Timedelta(hours=int(horas.group(3)), minutes=int(horas.group(4)))
            if fin <= inicio:  # el evento cruza la medianoche
                fin += pd.Timedelta(days=1)
            descripcion = linea.split(":**", 1)[-1]
            descripcion = re.split(r"[(,]", descripcion)[0]
            nombre = "_".join(sin_acentos(descripcion).split()[:4])
            ctx["eventos"].append((nombre, inicio, fin))
    return ctx


def en_oficina(ctx, t):
    if t.dayofweek not in ctx["horario"]:
        return False
    inicio, fin = ctx["horario"][t.dayofweek]
    return inicio <= t.hour < fin


def en_respaldo(ctx, t):
    hora, minuto = ctx["respaldo"]
    inicio = t.normalize() + pd.Timedelta(hours=hora, minutes=minuto)
    # también revisa el respaldo del día anterior por si cruza la medianoche
    return any(i <= t < i + pd.Timedelta(minutes=RESPALDO_MIN)
               for i in (inicio, inicio - pd.Timedelta(days=1)))


def evento_de_negocio(ctx, t):
    for nombre, inicio, fin in ctx["eventos"]:
        if inicio <= t <= fin:
            return nombre
    return None


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def cargar_metricas(carpeta=CARPETA):
    df = pd.read_csv(Path(carpeta) / "metricas.csv", parse_dates=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    # Hay celdas vacías: se rellenan con el último valor conocido (solo pasado).
    # Máximo 3 minutos: en un apagón largo no inventamos datos.
    df = df.ffill(limit=3)
    # Promedios móviles: solo usan minutos anteriores, nunca futuros
    df["cpu_5m"] = df["cpu"].rolling(5, min_periods=3).mean()
    df["disco_30m"] = df["disco"].rolling(30, min_periods=20).mean()
    df["errores_60m"] = df["errores"].rolling(60, min_periods=40).mean()
    df["cpu_60m"] = df["cpu"].rolling(60, min_periods=40).mean()
    df["cpu_max_2h"] = df["cpu"].rolling(120, min_periods=60).max()
    df["latencia_60m"] = df["latencia_ms"].rolling(60, min_periods=40).median()
    # El contexto del negocio viaja junto con los datos
    df.attrs["contexto"] = leer_contexto(carpeta, df.index[0].year)
    return df


def cargar_fallos_vpn(carpeta=CARPETA):
    """Lee logs.md y devuelve una lista de (timestamp, intentos_fallidos)."""
    fallos = []
    patron = re.compile(r"^(\S+)\s+\w+\s+VPN:.*?(\d+) intentos fallidos")
    for linea in (Path(carpeta) / "logs.md").read_text(encoding="utf-8").splitlines():
        if "VPN:" not in linea:
            continue
        m = patron.match(linea)
        if m:
            fallos.append((pd.Timestamp(m.group(1)), int(m.group(2))))
        elif "fallo la autenticacion" in linea:
            fallos.append((pd.Timestamp(linea.split()[0]), 1))
    return sorted(fallos)


def confianza(base, extra):
    """Base según qué tan directa es la prueba + bonus según qué tan lejos pasó el límite."""
    return round(min(CONFIANZA_MAX, base + max(0.0, extra)), 2)


# ---------------------------------------------------------------------------
# Reglas. Cada alerta: ("alerta", nombre, motivo, tipo, confianza)
#         Cada señuelo: ("senuelo", nombre, motivo)
# ---------------------------------------------------------------------------

def revisar_disco(df, t):
    ctx = df.attrs["contexto"]
    fila = df.loc[t]
    actual = fila["disco_30m"]
    if pd.isna(actual) or not (DISCO_MIN <= actual <= DISCO_MAX):
        return None
    # Tendencia: el promedio debe subir en cada bloque de 30 min (últimos 90 min)
    puntos = [t - pd.Timedelta(minutes=m) for m in (90, 60, 30, 0)]
    if puntos[0] < df.index[0]:
        return None
    valores = df["disco_30m"].reindex(puntos, method="ffill").tolist()
    sube_siempre = all(b > a for a, b in zip(valores, valores[1:]))
    if not sube_siempre:
        return None
    if en_respaldo(ctx, t):
        return ("senuelo", "Disco", "Respaldo nocturno")
    evento = evento_de_negocio(ctx, t)
    if evento:
        return ("senuelo", "Disco", f"Evento de negocio: {evento}")
    subida = actual - valores[0]
    return ("alerta", "Disco /data en riesgo",
            f"disco {actual:.1f}% y subiendo sin bajar ({valores[0]:.1f} -> {actual:.1f})",
            "deriva_disco", confianza(0.6, subida * 0.5))


def revisar_cpu(df, t):
    ctx = df.attrs["contexto"]
    cpu = df.loc[t, "cpu_5m"]
    if pd.isna(cpu) or cpu <= CPU_LIMITE:
        return None
    if en_oficina(ctx, t):
        return ("senuelo", "CPU", "CPU > 40% en horario de oficina")
    if en_respaldo(ctx, t):
        return ("senuelo", "CPU", "CPU > 40% en respaldo nocturno")
    evento = evento_de_negocio(ctx, t)
    if evento:
        return ("senuelo", "CPU", f"CPU > 40% en evento: {evento}")
    return ("alerta", "CPU elevada", f"CPU {cpu:.1f}% fuera de oficina y fuera del respaldo",
            "cpu_elevada", confianza(0.6, (cpu - CPU_LIMITE) / 100))


def revisar_errores(df, t):
    """Aviso temprano de ataque VPN: los errores suben sin parar durante 90 min
    mientras CPU, disco y latencia están normales (nada más explica los errores)."""
    ctx = df.attrs["contexto"]
    fila = df.loc[t]
    actual = fila["errores_60m"]
    if pd.isna(actual) or actual < ERRORES_LIMITE or en_oficina(ctx, t):
        return None
    puntos = [t - pd.Timedelta(minutes=m) for m in (90, 60, 30, 0)]
    if puntos[0] < df.index[0]:
        return None
    valores = df["errores_60m"].reindex(puntos, method="ffill").tolist()
    if not all(b > a for a, b in zip(valores, valores[1:])):
        return None
    todo_normal = (fila["cpu_60m"] < 32 and fila["disco_30m"] < 62
                   and fila["latencia_60m"] < 45 and fila["cpu_max_2h"] < CPU_PICO_MAX)
    if not todo_normal:
        return None
    return ("alerta", "Posible ataque VPN",
            f"errores subiendo sin causa visible ({valores[0]:.2f} -> {actual:.2f} por min)",
            "acceso_masivo_vpn", confianza(0.55, (actual - ERRORES_LIMITE) * 0.5))


def revisar_vpn(fallos, t):
    desde = t - pd.Timedelta(minutes=VPN_VENTANA_MIN)
    total = sum(n for (ts, n) in fallos if desde < ts <= t)  # solo pasado
    if total == 0:
        return None
    madrugada = MADRUGADA[0] <= t.hour < MADRUGADA[1]
    if VPN_MIN <= total <= VPN_MAX and madrugada:
        return ("alerta", "Posible ataque VPN",
                f"{total} intentos fallidos en {VPN_VENTANA_MIN} min de madrugada",
                "acceso_masivo_vpn", confianza(0.9, total / 1000))
    return ("senuelo", "VPN", f"intentos fallidos fuera del patrón (madrugada y más de {VPN_MIN - 1})")


def detectar(df, fallos, ventana):
    """Revisa cada minuto de la ventana. Devuelve (alertas, senuelos).
    Cada alerta: (timestamp, nombre, motivo, tipo, confianza)."""
    ultimo_visto = {}
    alertas, senuelos = [], {}
    for t in ventana:
        for resultado in (revisar_disco(df, t), revisar_cpu(df, t),
                          revisar_errores(df, t), revisar_vpn(fallos, t)):
            if resultado is None:
                continue
            if resultado[0] == "senuelo":
                _, nombre, motivo = resultado
                clave = f"{nombre}: {motivo}"
                senuelos[clave] = senuelos.get(clave, 0) + 1
                continue
            _, nombre, motivo, tipo, conf = resultado
            # Un solo aviso por incidente: mientras el problema siga apareciendo
            # (sin pausas largas) se considera el mismo incidente
            previo = ultimo_visto.get(tipo)
            ultimo_visto[tipo] = t
            if previo is not None and t - previo < pd.Timedelta(hours=HORAS_MISMO_INCIDENTE):
                continue
            alertas.append((t, nombre, motivo, tipo, conf))
    return alertas, senuelos


def guardar_csv(alertas, ruta, tenant="gracko"):
    """Guarda la entrega con el formato del reto: tenant,timestamp,confianza,tipo."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["tenant", "timestamp", "confianza", "tipo"])
        for t, _, _, tipo, conf in alertas:
            escritor.writerow([tenant, f"{t:%Y-%m-%dT%H:%M:%S}", f"{conf:.2f}", tipo])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", help='revisa FILAS minutos desde esa hora, ej. "2026-10-10 20:00"')
    parser.add_argument("--azar", action="store_true", help="revisa FILAS minutos desde un punto al azar")
    parser.add_argument("--carpeta", default=CARPETA, help="carpeta con metricas.csv, logs.md y contexto.md")
    parser.add_argument("--discord", action="store_true", help="envía los avisos al canal de Discord")
    parser.add_argument("--salida", help="guarda las alertas en este CSV, ej. alertas.csv")
    parser.add_argument("--gemini", action="store_true",
                        help="describe cada alerta en lenguaje sencillo con Gemini (nivel gratuito)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # para que la ñ se vea bien

    df = cargar_metricas(args.carpeta)
    fallos = cargar_fallos_vpn(args.carpeta)

    if args.inicio or args.azar:
        if args.inicio:
            pos = df.index.searchsorted(pd.Timestamp(args.inicio))
        else:
            pos = random.randint(0, len(df) - FILAS)
        ventana = df.index[pos:pos + FILAS]
    else:
        ventana = df.index  # toda la semana

    print(f"\nGracko | {len(ventana)} minutos revisados: {ventana[0]} -> {ventana[-1]}\n")

    alertas, senuelos = detectar(df, fallos, ventana)

    # Gemini solo se llama si hay alertas y si se pidió con --gemini
    descripciones = describir_alertas(alertas) if args.gemini and alertas else []

    print("\n=== AVISOS DE INCIDENCIA (enviar a Discord) ===")
    if not alertas:
        print("  Ninguna incidencia detectada.")
    for numero, (t, nombre, motivo, tipo, conf) in enumerate(alertas, start=1):
        print(f"\n  🚨 INCIDENCIA #{numero}: {nombre}")
        print(f"     Detectada: {t:%Y-%m-%d %H:%M}")
        print(f"     Tipo:      {tipo}  (confianza {conf:.2f})")
        print(f"     Motivo:    {motivo}")
        if descripciones:
            print(f"     Para el jefe: {descripciones[numero - 1]}")

    print("\n=== SEÑUELOS DESCARTADOS (minutos) ===")
    if not senuelos:
        print("  Ninguno.")
    for motivo, n in senuelos.items():
        print(f"  {n:>3} min  {motivo}")
    print()

    if args.salida:
        guardar_csv(alertas, args.salida)
        print(f"💾 Alertas guardadas en {args.salida}")

    if args.discord:
        enviar_a_discord(alertas, descripciones=descripciones)


if __name__ == "__main__":
    main()
