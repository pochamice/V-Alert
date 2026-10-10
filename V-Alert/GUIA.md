# Guía del kit — «Antes de que suene el teléfono»

Esta carpeta junta todo el contexto en un solo lugar:

| Archivo | Contenido |
|---|---|
| `reto.md` | Copia del reto del patrocinador (`ZickitReto.md`) |
| `gracko.md`, `gramo.md`, `kaiku.md`, `ttr.md` | Contexto de negocio de cada empresa |
| `GUIA.md` | Este documento |

> Los `contexto.md` de cada empresa son **idénticos en las 54 corridas** (verificado por hash), por eso basta una
> copia por empresa. Los originales siguen en `data/` para no romper la estructura que espera el evaluador.

## 1. Cómo está organizado el kit

```
data/
├── gracko/ gramo/ kaiku/ ttr/      ← una corrida de ejemplo suelta, para explorar
├── todos_metricas.csv
├── _solucion/                      ← respuestas de esa corrida de ejemplo
└── corridas/
    ├── corrida_01 … corrida_54/    ← 54 semanas simuladas, del 8 al 14 de oct
    │   ├── <empresa>/contexto.md   ← qué es "normal" (horarios y eventos programados)
    │   ├── <empresa>/metricas.csv  ← 1 fila por minuto (~9 200 filas)
    │   ├── <empresa>/logs.md       ← 3 secciones: servidor, firewall y app
    │   └── todos_metricas.csv      ← las 4 empresas juntas, con columna tenant
    └── corrida_01…10/_solucion/etiquetas.csv   ← solo existe en las 10 primeras
```

Para qué sirve cada archivo:

- **`metricas.csv`** es la señal principal: `cpu, ram, disco, latencia_ms, errores`. Tiene celdas vacías, así que hay que
  limpiarlo antes de usarlo.
- **`logs.md`** trae las pistas finas. Casi todo es ruido (`escaneo de puertos`, `webhook sin respuesta`,
  `sync_contactos`…). Las pocas líneas que importan son del tipo `disco /data al N%`, `VPN: N intentos fallidos` y
  `cpu de fs-01 al N% sostenido`.
- **`contexto.md`** sirve para no alertar por los señuelos. Si a las 23:00 sube el disco y el contexto dice
  "Respaldo nocturno 23:00", eso no es un incidente.
- **`etiquetas.csv`** tiene el formato `inicio_incidente,tipo,es_real`. `inicio_incidente` es el momento del
  **impacto**, y los síntomas aparecen antes. Por ejemplo, en gracko el disco empieza a subir el día 9 y el impacto
  ocurre el 11 a las 23:00, cuando el respaldo falla por falta de espacio. El objetivo es alertar entre esos dos
  momentos.

## 2. Cómo usarlo

1. **Usar `_solucion` solo para calificarse.** El reto dice que no se use para entrenar ni para predecir. Con ese
   archivo midan detectados contra falsas alarmas y los minutos de anticipación de cada alerta. Si quieren afinar
   umbrales con las corridas 01–10, conviene confirmarlo antes con los organizadores.
2. **Usar las corridas 11–54 (sin etiquetas)** para ver qué tan variable es lo "normal" y para probar el sistema contra
   datos que no han visto.
3. **Procesar minuto a minuto, solo hacia adelante.** En el minuto `t` solo se pueden usar datos hasta `t`; lo más
   fácil es que el código lo cumpla desde el diseño. La salida es una lista de alertas con
   `tenant, timestamp, confianza, tipo`.

### Riesgos

- En las corridas 01–10 los incidentes caen **siempre en la misma fecha y hora**; lo único que cambia es el ruido. Si
  se ponen fechas fijas en el código, la evaluación local sale perfecta, pero probablemente los organizadores califican
  con datos distintos. **Detecten patrones, no horas.**
- `scripts/generar.py` es el script que genera los datos, así que en la práctica es la hoja de respuestas. No usarlo:
  lo de "solo usen los datos del kit" apunta a eso.

## 3. Empresa recomendada como punto de partida: gracko

| | gracko | kaiku | gramo | ttr |
|---|---|---|---|---|
| Señuelos explicados en el contexto | ✅ todos (respaldo 23:00, carga masiva vie 17:00, cierre de nómina lun 10:00) | ✅ casi todos | ⚠️ el señuelo `reporte_rutas_nocturno` (02:00 diario) **no aparece** en su contexto | ⚠️ `pedido_urgente` no aparece |
| Tipos de incidente | 3 muy distintos entre sí | 3, dos de ellos en el checkout (se confunden) | 3 | 3 |
| Horario | oficina simple (L–V y sábado en la mañana) | 24/7 | mixto | mixto |

### Incidentes reales de gracko (iguales en todas las corridas etiquetadas)

| Incidente | Pista | Detector sugerido |
|---|---|---|
| `deriva_disco` (impacto 11/oct 23:00) | `disco` sube de ~58% a ~97% durante días. El contexto lo advierte: "/data sin alerta de capacidad" | Tendencia o regresión del disco que **no** se reinicia después del respaldo. Da más de un día de anticipación |
| `acceso_masivo_vpn` (13/oct 00:30) | Logs del firewall: `VPN: N intentos fallidos desde …` y cuentas bloqueadas | Contar intentos fallidos de VPN por ventana, sobre todo fuera de horario |
| `cpu_intermitente_erp` (14/oct 09:20) | CPU de ~45% de madrugada (fuera de horario), y luego `cpu de fs-01 al N% sostenido` y latencia del ERP | CPU alta cuando no hay oficina ni respaldo |

Los señuelos (respaldo diario, carga masiva y cierre de nómina) se descartan con una tabla de "ventanas esperadas"
sacada de `gracko.md`.

### Orden sugerido

1. Detector de tendencia del disco (el que más anticipación gana).
2. Contador de intentos fallidos de VPN en los logs del firewall.
3. CPU alta fuera de horario.
4. Cuando funcione en gracko, adaptar la misma estructura a kaiku cambiando el contexto y las reglas.
