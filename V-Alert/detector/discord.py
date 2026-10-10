"""Envía los avisos de incidencia a un canal de Discord por webhook.

El enlace del webhook se guarda en detector/webhook.txt (no lo compartas:
quien lo tenga puede escribir en tu canal).
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

ARCHIVO_WEBHOOK = Path(__file__).resolve().parent / "webhook.txt"
COLOR_ROJO = 0xE74C3C


def leer_webhook():
    if not ARCHIVO_WEBHOOK.exists():
        return None
    url = ARCHIVO_WEBHOOK.read_text(encoding="utf-8").strip()
    return url or None


def enviar_a_discord(alertas, tenant="gracko", descripciones=None):
    """Manda todas las alertas en un solo mensaje. Devuelve True si salió bien.
    Si hay descripciones (de Gemini), se muestran como texto principal de cada tarjeta."""
    url = leer_webhook()
    if not url:
        print(f"⚠️  No encontré el webhook. Pega el enlace en {ARCHIVO_WEBHOOK}")
        return False
    if not alertas:
        print("No hay incidencias que enviar a Discord.")
        return True

    tarjetas = []
    for numero, (t, nombre, motivo, tipo, conf) in enumerate(alertas[:10], start=1):  # máx. 10
        tarjeta = {
            "title": f"🚨 Incidencia #{numero}: {nombre}",
            "color": COLOR_ROJO,
            "fields": [
                {"name": "Empresa", "value": tenant, "inline": True},
                {"name": "Detectada", "value": f"{t:%Y-%m-%d %H:%M}", "inline": True},
                {"name": "Confianza", "value": f"{conf:.0%}", "inline": True},
                {"name": "Tipo", "value": tipo, "inline": True},
                {"name": "Motivo", "value": motivo, "inline": False},
            ],
        }
        if descripciones:
            tarjeta["description"] = descripciones[numero - 1]
        tarjetas.append(tarjeta)

    mensaje = {
        "username": "Alerta temprana",
        "content": f"**{len(alertas)} incidencia(s) detectada(s) en {tenant}**",
        "embeds": tarjetas,
    }
    peticion = urllib.request.Request(
        url,
        data=json.dumps(mensaje).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "detector-zikit"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=10):
            pass
    except urllib.error.HTTPError as e:
        print(f"❌ Discord respondió con error {e.code}: {e.read().decode('utf-8', 'ignore')}")
        return False
    except urllib.error.URLError as e:
        print(f"❌ No se pudo conectar con Discord: {e.reason}")
        return False
    print(f"✅ Enviadas {len(tarjetas)} incidencia(s) a Discord.")
    return True
