# V-Alert

Sistema de alerta temprana de futuros incidentes de TI. Pretende ser un vigía de posibles incidentes aplicando métodos estadísticos que detectan patrones de errores reales sin falsos positivos.

Proyecto para el reto «Antes de que suene el teléfono»: sistema de alerta temprana para una pyme (Gracko, despacho contable): detecta problemas de TI **antes** de que el cliente llame enojado, sin falsas alarmas, y los explica al dueño del negocio en lenguaje sencillo.

## Resultados

Probado en las 54 corridas del kit. Se calificó con las 10 que traen solución oficial:

| Incidente real | Detectado | Anticipación |
|---|---|---|
| Disco `/data` se llena | 10/10 | ~49 h antes |
| Ataque por VPN | 10/10 | ~2 h antes |
| CPU intermitente del ERP | 10/10 | ~14 h antes |

**30/30 incidentes detectados, 0 falsas alarmas**, un solo aviso por incidente.

## Cómo funciona

Revisa los datos minuto a minuto, usando solo el pasado, con 4 reglas:

1. **Disco:** uso entre 60 % y 70 % que sube sin bajar durante 90 min.
2. **CPU:** más de 40 % fuera del horario de oficina, del respaldo nocturno y de los eventos del negocio.
3. **Ataque VPN (aviso temprano):** errores que suben sin parar mientras todo lo demás está normal.
4. **Ataque VPN (confirmación):** más de 12 intentos fallidos de VPN de madrugada en los logs.

Los horarios, el respaldo y los eventos se leen de `contexto.md`, así que no hay fechas fijas en el código. Explicación completa, sin necesidad de saber Python: [EXPLICACION_DETECTOR.md](EXPLICACION_DETECTOR.md).

## Requisitos

- Python 3.13
- `pip install pandas`

## Uso

```bash
python detector/detector.py                      # avisos de la corrida de ejemplo (data/gracko)
python detector/detector.py --salida alertas.csv # guarda la entrega: tenant,timestamp,confianza,tipo
python detector/detector.py --gemini             # explica cada alerta en 3 oraciones para el jefe
python detector/detector.py --discord            # envía los avisos a un canal de Discord
```

### Opcionales: Discord y Gemini

Estos archivos son secretos y **no** están en el repositorio:

- `detector/webhook.txt`: URL del webhook del canal de Discord.
- `detector/gemini_key.txt`: clave de la API de Gemini (nivel gratuito, modelo `gemini-3.5-flash-lite`).

Gemini solo se llama cuando hay alertas, con límites propios: 5 llamadas por ejecución y 20 por día. Si no hay clave o algo falla, se usa un texto de respaldo sin costo.

### Evaluación con el kit completo

El repositorio solo incluye la corrida de ejemplo (`data/gracko/`). Para usar `evaluar.py`:

1. Descarga el kit de los organizadores: <https://github.com/brunovillarrrrrr/zikit-dataset>.
2. Copia su carpeta `data/corridas/` dentro de `data/`.
3. Ejecuta:

```bash
python detector/evaluar.py   # genera salidas/corrida_XX.csv y califica
```

## Estructura

```
detector/
  detector.py   reglas, lectura de contexto, consola y CSV
  evaluar.py    prueba en las 54 corridas
  discord.py    envío por webhook
  gemini.py     descripciones en lenguaje sencillo
data/gracko/    corrida de ejemplo del kit
salidas/        entregas CSV de las 54 corridas
```

## Créditos

Datos: kit «Antes de que suene el teléfono» de [brunovillarrrrrr/zikit-dataset](https://github.com/brunovillarrrrrr/zikit-dataset), licencia [MIT](LICENSE).
