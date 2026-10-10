"""Describe cada alerta en 3 oraciones sencillas usando Gemini (nivel gratuito).

Reglas de ahorro:
- Solo se llama cuando hay una alerta (nunca en otro momento).
- Modelo Flash-Lite, sin razonamiento extra y con respuesta corta.
- Límites propios muy por debajo del nivel gratuito: pocas llamadas por
  ejecución y por día, con espera entre llamadas. Nunca se reintenta.
- Si algo falla o se ve raro, se avisa en la consola y se usa un texto de
  respaldo que no cuesta nada.

La clave se guarda en detector/gemini_key.txt (no compartir ni subir a GitHub).
"""
import json
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
ARCHIVO_CLAVE = CARPETA / "gemini_key.txt"
ARCHIVO_USO = CARPETA / "gemini_uso.json"

MODELO = "gemini-3.5-flash-lite"  # 2.5 ya no está disponible para cuentas nuevas
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent"

# --- Límites propios (puedes bajarlos, no conviene subirlos) ---
MAX_POR_EJECUCION = 5        # llamadas máximas cada vez que corre el detector
MAX_POR_DIA = 20             # llamadas máximas por día (se cuentan en gemini_uso.json)
ESPERA_SEGUNDOS = 6          # pausa entre llamadas (máx. 10 por minuto)
MAX_TOKENS_RESPUESTA = 150   # unas 3 oraciones cortas
TOKENS_SOSPECHOSOS = 1000    # si una llamada gasta más que esto, se reporta

# Texto de respaldo (gratis) por si Gemini no responde
RESPALDO = {
    "deriva_disco": ("El espacio donde se guardan los archivos de los clientes se está llenando poco a poco. "
                     "Si se llena por completo, el equipo no podrá guardar ni abrir expedientes. "
                     "Pida a su encargado de sistemas que libere espacio o mueva archivos antiguos hoy."),
    "acceso_masivo_vpn": ("Hay señales de que alguien de fuera está intentando entrar a la red de la oficina. "
                          "Por ahora no hay daño confirmado, pero conviene actuar pronto. "
                          "Pida a su encargado de sistemas que revise y bloquee los accesos remotos sospechosos."),
    "cpu_elevada": ("El servidor de la oficina está trabajando más de lo normal sin una razón clara. "
                    "Esto puede hacer que el sistema contable se vuelva lento mañana. "
                    "Pida a su encargado de sistemas que revise qué programa está consumiendo recursos."),
}

INSTRUCCIONES = """Eres el asistente de un despacho contable pequeño (una pyme).
Le escribes al dueño del negocio, que NO sabe de tecnología.
Escribe EXACTAMENTE 3 oraciones en español, claras y tranquilas, sin palabras técnicas
(no uses: CPU, VPN, servidor, latencia, logs, porcentajes).
1. Qué está pasando, en palabras sencillas.
2. Por qué importa para el negocio, sin asustar.
3. Una solución breve y concreta que puede pedir o hacer hoy.
La solución debe ser segura: nunca recomiendes apagar equipos, borrar archivos ni cambiar
nada por su cuenta; lo correcto es pedir una revisión al encargado de sistemas o al proveedor.
Ejemplo: "El disco está casi en su capacidad límite. Si se llena, el equipo no podrá guardar
archivos. Se recomienda pedir una revisión hoy para liberar espacio."
Responde solo con las 3 oraciones."""


class Presupuesto:
    """Cuenta las llamadas para no pasar nunca los límites."""

    def __init__(self):
        self.en_esta_ejecucion = 0
        self.ultima_llamada = 0.0
        self.detenido = False
        hoy = date.today().isoformat()
        try:
            uso = json.loads(ARCHIVO_USO.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            uso = {}
        self.hoy = hoy
        self.hoy_usadas = uso.get("llamadas", 0) if uso.get("fecha") == hoy else 0

    def puede_llamar(self):
        if self.detenido:
            return False
        if self.en_esta_ejecucion >= MAX_POR_EJECUCION:
            print(f"   ℹ️  Límite de {MAX_POR_EJECUCION} llamadas por ejecución alcanzado; uso texto de respaldo.")
            return False
        if self.hoy_usadas >= MAX_POR_DIA:
            print(f"   ℹ️  Límite de {MAX_POR_DIA} llamadas por día alcanzado; uso texto de respaldo.")
            return False
        return True

    def registrar(self):
        self.en_esta_ejecucion += 1
        self.hoy_usadas += 1
        self.ultima_llamada = time.monotonic()
        ARCHIVO_USO.write_text(json.dumps({"fecha": self.hoy, "llamadas": self.hoy_usadas}), encoding="utf-8")

    def esperar_turno(self):
        falta = ESPERA_SEGUNDOS - (time.monotonic() - self.ultima_llamada)
        if self.ultima_llamada and falta > 0:
            time.sleep(falta)


def reportar_sospecha(mensaje):
    print(f"\n   🚩 SOSPECHOSO (revisar costos): {mensaje}")
    print("      Gemini quedó apagado en esta ejecución. Revisa https://aistudio.google.com (facturación y uso).\n")


def leer_clave():
    try:
        clave = ARCHIVO_CLAVE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return clave or None


def pedir_a_gemini(clave, alerta, presupuesto):
    """Hace UNA llamada. Devuelve el texto o None si falla (nunca reintenta)."""
    t, nombre, motivo, tipo, conf = alerta
    datos = (f"Alerta detectada a las {t:%H:%M} del {t:%d/%m}: {nombre}. "
             f"Detalle técnico (tradúcelo a lenguaje sencillo): {motivo}. Tipo: {tipo}.")
    cuerpo = {
        "systemInstruction": {"parts": [{"text": INSTRUCCIONES}]},
        "contents": [{"role": "user", "parts": [{"text": datos}]}],
        "generationConfig": {
            "maxOutputTokens": MAX_TOKENS_RESPUESTA,
            "temperature": 0.3,
            "thinkingConfig": {"thinkingLevel": "minimal"},  # sin razonamiento extra = menos tokens
        },
    }
    peticion = urllib.request.Request(
        URL,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": clave},
        method="POST",
    )

    presupuesto.esperar_turno()
    presupuesto.registrar()  # se cuenta antes de enviar, aunque falle
    try:
        with urllib.request.urlopen(peticion, timeout=20) as r:
            respuesta = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Cualquier error apaga Gemini en esta ejecución: no gastamos más llamadas
        presupuesto.detenido = True
        detalle = e.read().decode("utf-8", "ignore")
        if e.code == 429:
            reportar_sospecha("Gemini respondió 429 (límite de uso alcanzado). No se reintenta.")
        elif "billing" in detalle.lower() or "quota" in detalle.lower():
            reportar_sospecha(f"error {e.code} mencionando facturación o cuota: {detalle[:200]}")
        else:
            print(f"   ❌ Gemini respondió con error {e.code}: {' '.join(detalle.split())[:200]}")
            print("      Gemini quedó apagado en esta ejecución; uso texto de respaldo.")
        return None
    except (urllib.error.URLError, TimeoutError) as e:
        presupuesto.detenido = True
        print(f"   ❌ No se pudo conectar con Gemini: {e}. Uso texto de respaldo.")
        return None

    uso = respuesta.get("usageMetadata", {})
    total = uso.get("totalTokenCount", 0)
    if total > TOKENS_SOSPECHOSOS:
        reportar_sospecha(f"una sola descripción gastó {total} tokens (esperado: ~300).")
        presupuesto.detenido = True
    try:
        texto = respuesta["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        print("   ❌ Gemini no devolvió texto.")
        return None
    print(f"   🤖 Gemini ({MODELO}): {total} tokens usados · llamadas hoy: "
          f"{presupuesto.hoy_usadas}/{MAX_POR_DIA}")
    return " ".join(texto.split())


def describir_alertas(alertas):
    """Devuelve una descripción de 3 oraciones por alerta (Gemini o texto de respaldo)."""
    if not alertas:
        return []  # sin alertas no se llama a Gemini
    clave = leer_clave()
    if not clave:
        print(f"⚠️  No encontré la clave de Gemini en {ARCHIVO_CLAVE}; uso texto de respaldo.")
    presupuesto = Presupuesto()
    descripciones = []
    for alerta in alertas:
        texto = None
        if clave and presupuesto.puede_llamar():
            texto = pedir_a_gemini(clave, alerta, presupuesto)
        if not texto:
            texto = RESPALDO.get(alerta[3], "Se detectó un posible problema. Pida una revisión a su encargado de sistemas.")
        descripciones.append(texto)
    return descripciones
