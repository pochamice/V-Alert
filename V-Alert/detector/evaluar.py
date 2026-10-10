"""Prueba el detector en las 54 corridas de gracko (toda la semana de cada una).

Guarda la entrega de cada corrida en salidas/corrida_XX.csv y califica leyendo
ese mismo archivo (así comprobamos que el CSV entregado es correcto).
_solucion solo se usa aquí para calificar, nunca dentro del detector.

Uso:
    python detector/evaluar.py
"""
import sys
from pathlib import Path

import pandas as pd

from detector import cargar_fallos_vpn, cargar_metricas, detectar, guardar_csv

RAIZ = Path(__file__).resolve().parent.parent
CORRIDAS = RAIZ / "data" / "corridas"
SALIDAS = RAIZ / "salidas"
COLUMNAS = ["tenant", "timestamp", "confianza", "tipo"]

# Qué tipo de alerta corresponde a cada incidente real
TIPO_ALERTA = {
    "deriva_disco": "deriva_disco",
    "acceso_masivo_vpn": "acceso_masivo_vpn",
    "cpu_intermitente_erp": "cpu_elevada",
}
# Una alerta cuenta para un incidente si sale hasta 3 días antes o 1 hora después
# (el disco empieza a subir ~2 días antes del incidente)
ANTES, DESPUES = pd.Timedelta(days=3), pd.Timedelta(hours=1)


def calificar(alertas, etiquetas):
    reales = etiquetas[etiquetas["es_real"]]
    usadas = set()
    resultado = {}
    for _, inc in reales.iterrows():
        tipo = TIPO_ALERTA.get(inc["tipo"])
        validas = [a for a in alertas if a[1] == tipo
                   and inc["inicio_incidente"] - ANTES <= a[0] <= inc["inicio_incidente"] + DESPUES]
        usadas.update(validas)
        if validas:
            primera = validas[0][0]
            resultado[inc["tipo"]] = (inc["inicio_incidente"] - primera).total_seconds() / 60
        else:
            resultado[inc["tipo"]] = None
    falsas = [a for a in alertas if a not in usadas]
    return resultado, falsas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{'corrida':<11} {'alertas':>7}  {'disco':>9} {'vpn':>9} {'cpu':>9}  falsas")
    totales = {"detectados": 0, "posibles": 0, "falsas": 0}

    for carpeta in sorted(CORRIDAS.iterdir()):
        df = cargar_metricas(carpeta / "gracko")
        fallos = cargar_fallos_vpn(carpeta / "gracko")
        alertas, _ = detectar(df, fallos, df.index)

        # Guardar la entrega y volver a leerla para calificar desde el archivo
        archivo = SALIDAS / f"{carpeta.name}.csv"
        guardar_csv(alertas, archivo)
        entrega = pd.read_csv(archivo, parse_dates=["timestamp"])
        assert list(entrega.columns) == COLUMNAS, f"columnas incorrectas en {archivo}"
        assert entrega["confianza"].between(0, 1).all(), f"confianza fuera de 0-1 en {archivo}"
        alertas = list(zip(entrega["timestamp"], entrega["tipo"]))

        sol = carpeta / "_solucion" / "gracko" / "etiquetas.csv"
        if not sol.exists():
            print(f"{carpeta.name:<11} {len(alertas):>7}  (sin solución para comparar)")
            continue

        etiquetas = pd.read_csv(sol, parse_dates=["inicio_incidente"])
        etiquetas["es_real"] = etiquetas["es_real"].astype(str).str.lower() == "true"
        resultado, falsas = calificar(alertas, etiquetas)

        celdas = []
        for tipo in TIPO_ALERTA:
            minutos = resultado.get(tipo)
            celdas.append("  FALLÓ" if minutos is None else f"{minutos / 60:+.1f} h")
        print(f"{carpeta.name:<11} {len(alertas):>7}  {celdas[0]:>9} {celdas[1]:>9} {celdas[2]:>9}  {len(falsas)}")

        totales["detectados"] += sum(m is not None for m in resultado.values())
        totales["posibles"] += len(resultado)
        totales["falsas"] += len(falsas)

    print("\n(+ h = horas de anticipación; negativo = avisó después de que empezó)")
    print(f"Incidentes detectados: {totales['detectados']}/{totales['posibles']}")
    print(f"Falsas alarmas: {totales['falsas']}")
    print(f"Entregas guardadas en {SALIDAS}")


if __name__ == "__main__":
    main()
