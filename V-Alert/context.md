# context.md — Punto general del proyecto

> Base de conocimiento del equipo para el hackathon. Última actualización: 2026-10-10.

## 1. Objetivo del hackathon

**Reto:** «Antes de que suene el teléfono». Una pyme tiene un problema de TI y se entera cuando el cliente llama enojado. Somos el **sistema de alerta temprana**: avisar de incidentes reales **antes del impacto**, sin falsas alarmas.

**Alcance del equipo:** solo la empresa **gracko** (despacho contable y fiscal, 12 empleados). Las otras empresas del kit (gramo, kaiku, ttr) se eliminaron del dataset para enfocarnos.

**Entregable:** lista de alertas en CSV con el formato:

```
tenant,timestamp,confianza,tipo
```

| Campo | Significado | Obligatorio |
|---|---|---|
| `tenant` | Empresa (`gracko`) | Sí |
| `timestamp` | Momento en que se lanza la alerta | Sí |
| `confianza` | Qué tan seguros estamos (0 a 1) | Opcional |
| `tipo` | Incidente que creemos que viene | Opcional |

**Cómo se califica:** incidentes reales detectados antes del impacto, pocas falsas alarmas y más anticipación.

**Reglas del reto:**
- Solo datos del kit. **No mirar el futuro:** una alerta en el minuto *t* solo usa datos hasta *t*.
- `_solucion/` es del evaluador: solo para autocalificarse, nunca para detectar.
- `scripts/generar.py` es la "hoja de respuestas": no usarlo.
- **Detectar patrones, no fechas fijas:** los jueces probablemente califican con datos distintos.

## 2. Stack tecnológico

| Herramienta | Uso |
|---|---|
| Python 3.13 | Lenguaje (`C:\Users\Michelle\AppData\Local\Programs\Python\Python313`, ya está en el PATH del usuario) |
| pandas | Leer CSV y calcular promedios móviles |
| Librería estándar (`csv`, `re`, `urllib`, `argparse`, `pathlib`) | Todo lo demás; **sin librerías extra** |
| Discord (webhook) | Envío de alertas al canal del equipo |
| Gemini API (`gemini-3.5-flash-lite`, nivel gratuito) | Explica cada alerta en 3 oraciones sencillas para el jefe (experimental, opcional con `--gemini`) |
| VS Code | Editor; terminal PowerShell |

Costo operativo: prácticamente cero (sin IA pagada ni servicios de nube obligatorios).

## 3. Datos (por corrida, carpeta `gracko/`)

| Archivo | Contenido |
|---|---|
| `metricas.csv` | 1 fila por minuto (9 200 filas, 2026-10-08 08:00 → 2026-10-14 17:19): `cpu, ram, disco, latencia_ms, errores`. Tiene celdas vacías y apagones |
| `logs.md` | Logs de servidor, firewall y app (incluye intentos fallidos de VPN) |
| `contexto.md` | Horario de oficina, respaldo nocturno y eventos de negocio |

- `data/gracko/`: corrida de ejemplo. `data/corridas/corrida_01..54/`: 54 corridas. Solo las 01–10 traen `_solucion/`.
- En las corridas de práctica los 3 incidentes reales caen siempre en la misma fecha; solo cambia el ruido.

| Incidente real | Inicio |
|---|---|
| `deriva_disco` | 2026-10-11 23:00 |
| `acceso_masivo_vpn` | 2026-10-13 00:30 |
| `cpu_intermitente_erp` | 2026-10-14 09:20 |

**Señuelos (no son incidentes):** horario de oficina (L–V 08–18, sáb 09–13), respaldo nocturno (23:00–23:40), carga masiva de declaraciones (vie 9, 17:00–19:30), cierre de nómina (lun 12, 10:00–14:00), 9 intentos fallidos del usuario "contador".

## 4. Logros completados (NO TOCAR sin orden directa)

1. **Detector con 4 reglas** (`detector/detector.py`):
   - **Disco:** promedio de 30 min entre 60 y 70 % y subiendo en cada bloque de 30 min durante 90 min.
   - **CPU:** promedio de 5 min > 40 % fuera de oficina, del respaldo y de los eventos.
   - **VPN temprano:** errores (promedio 1 h) ≥ 0.5/min y subiendo 90 min, con CPU, disco y latencia normales y sin picos de CPU ≥ 45 % en 2 h.
   - **VPN logs:** más de 12 intentos fallidos en 35 min de madrugada (00:00–06:00).
2. **Robustez:** relleno de huecos de máximo 3 min (los apagones no se inventan); respaldo extendido a 45 min; **un solo aviso por incidente** (se repite solo si el problema desaparece > 12 h).
3. **Contexto leído de `contexto.md`** (horario, respaldo y eventos): sin fechas fijas en el código.
4. **Salidas:** consola (incidencias con tipo y confianza, más resumen de señuelos), Discord (`--discord`, probado y funcionando) y CSV (`--salida`).
5. **Evaluación** (`detector/evaluar.py`): genera `salidas/corrida_01..54.csv`, valida su formato y califica leyendo esos archivos.
6. **Resultado actual:** **30/30 incidentes detectados, 0 falsas alarmas**, 3 alertas por corrida.

| Incidente | Anticipación |
|---|---|
| Disco | ~49 h antes |
| VPN | ~2 h antes (1.6–2.6 h) |
| CPU | ~14 h antes |

7. **Gemini** (`detector/gemini.py`): solo se llama si hay alertas y con `--gemini`. Límites: máx. 5 llamadas por ejecución y 20 por día, 6 s entre llamadas, sin razonamiento extra (~300 tokens por alerta). Se apaga al primer error y nunca reintenta. Reporta lo sospechoso de costos (429, facturación, demasiados tokens). Si falla, usa un texto de respaldo gratis.
8. **Documentación:** `EXPLICACION_DETECTOR.md` (explicación técnica para personas sin conocimientos de Python).

## 5. Archivos clave

| Ruta | Para qué |
|---|---|
| `detector/detector.py` | Lógica del detector, reglas, contexto, consola y CSV |
| `detector/discord.py` | Envío de alertas por webhook |
| `detector/evaluar.py` | Prueba en las 54 corridas y calificación |
| `detector/webhook.txt` | URL secreta del webhook (**no compartir ni subir a GitHub**) |
| `detector/gemini.py` | Descripciones con Gemini y límites de gasto |
| `detector/gemini_key.txt` | Clave de Gemini (**secreta**) |
| `detector/gemini_uso.json` | Contador de llamadas del día |
| `.gitignore` | Excluye los secretos y el contador |
| `salidas/` | Entregas CSV por corrida |
| `alertas.csv` | Entrega de la corrida de ejemplo |
| `EXPLICACION_DETECTOR.md` | Explicación para la presentación |
| `contexto_presentacion.md`, `GUIA.md`, `archivocontexto.md` | Contexto original del reto |

**Comandos:**

```
python detector/detector.py                        # toda la semana, en consola
python detector/detector.py --salida alertas.csv   # guarda la entrega
python detector/detector.py --discord              # envía a Discord
python detector/detector.py --carpeta data/corridas/corrida_05/gracko
python detector/detector.py --gemini --discord     # alertas explicadas para el jefe, en Discord
python detector/evaluar.py                         # 54 corridas (~1-2 min, nunca llama a Gemini)
```

Respaldos en `Downloads\zikit-dataset-main\`: `respaldo_zikit_completo.tar.gz` (dataset original) y `respaldo_antes_gemini_20261010_0644.tar.gz` (proyecto antes de Gemini).

## 6. Estado actual

**Tarea inmediata:** pendientes pequeños antes de la presentación.

- [x] Crear `.gitignore` para excluir los secretos.
- [ ] Preguntar a los asesores qué conviene y qué no en el uso de la API de Gemini (costos).
- [ ] Confirmar en AI Studio que el proyecto de la clave **no tiene facturación activada**.
- [ ] Al terminar el hackathon, **cambiar la clave de Gemini** (se compartió en el chat).
- [ ] Preguntar a los organizadores:
  - ¿Cuánta anticipación máxima aceptan? (el aviso del disco llega ~49 h antes)
  - ¿Se vale ajustar los umbrales mirando las corridas 01–10?
- [ ] Preparar la demo (consola + Discord) y la presentación.

**Riesgos conocidos:**
- Umbrales ajustados con las corridas de práctica: podrían rendir menos con datos nuevos. La regla de logs de VPN queda como respaldo.
- El aviso temprano de VPN tiene confianza baja (0.55) porque es una pista indirecta.
- El análisis de logs depende del formato de texto actual (`VPN: N intentos fallidos`).

## 7. Reglas de operación

1. Este archivo es la referencia principal; actualizarlo cuando algo cambie.
2. Respuestas concisas y orientadas a la acción, en español y paso a paso (el programador del equipo es principiante).
3. No refactorizar lo que está en «Logros completados» sin orden directa.
4. Basar las sugerencias en «Estado actual».
5. Volver a correr `evaluar.py` después de cualquier cambio en las reglas.
