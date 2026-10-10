# Brief para generar la documentación y presentación del proyecto

> **Para la IA que recibe este documento:** aquí está todo el contexto de un proyecto de hackathon. Tu tarea es ayudar
> a la líder del equipo a crear la **documentación y la presentación** de la solución. Lee la sección 8 («Qué se
> necesita de ti») antes de empezar. La líder es principiante en programación: usa un lenguaje claro y sin jerga
> innecesaria.

---

## 1. Situación del equipo

- **Evento:** hackathon (concurso de programación), octubre de 2026, en un gimnasio con más de 40 equipos.
- **Reto:** «Antes de que suene el teléfono», propuesto por un patrocinador.
- **Rol de quien te escribe:** líder del equipo. Ella se encarga de la **documentación y la presentación**; el resto del
  equipo programa la solución.
- **Nivel técnico:** principiante. El equipo usa Python 3.13 y pandas.
- **Contratiempo:** se fue la luz en el lugar del evento, así que hay que aprovechar bien el tiempo y la batería.
- **Consejo que recibió la líder:** hacer la presentación **más comercial y con menos metodología** (ver sección 6).

---

## 2. El reto, explicado simple

Una **PyME** (empresa pequeña o mediana) tiene un problema de TI (servidor lleno, ataque, sistema lento...) y **se
entera cuando un cliente llama enojado**. La misión es construir un **sistema de alerta temprana** que avise **antes
de esa llamada**.

- Mientras **más temprano** se avise de un incidente real, mejor.
- Si se avisa **por todo**, nadie le va a creer al sistema. Las falsas alarmas restan puntos.

Analogía útil para la presentación: es como una **alarma de humo**. Tiene que sonar con el fuego, pero no cada vez que
alguien hace pan tostado.

### Qué hay que entregar

Una lista de alertas. Cada alerta lleva:

| Campo | Significado | ¿Obligatorio? |
|---|---|---|
| `tenant` | La empresa (gracko, gramo, kaiku o ttr) | Sí |
| `timestamp` | El momento en que se lanza la alerta | Sí |
| `confianza` | Qué tan seguros están (de 0 a 1) | Opcional |
| `tipo` | Qué incidente creen que viene | Opcional |

### Cómo se califica

1. **Incidentes reales detectados antes del impacto.**
2. **Pocas falsas alarmas.**
3. **Tiempo de anticipación:** cuanto más temprano, mejor.

### Reglas

- Solo se pueden usar los datos del kit.
- **No se vale ver el futuro:** una alerta en el minuto *t* solo puede usar datos hasta *t*.
- Las carpetas `_solucion` son del evaluador: no se pueden usar para entrenar ni para predecir, solo para
  autocalificarse.
- `scripts/generar.py` (el programa que generó los datos) no se debe usar, porque en la práctica es la hoja de
  respuestas.
- En las corridas de práctica los incidentes caen siempre en la misma fecha. **Hay que detectar patrones, no poner
  fechas fijas en el código**, porque probablemente los jueces califican con datos distintos.

### Lo difícil

- Cada empresa tiene **3 incidentes reales** por corrida. Algunos dan señales **40 minutos antes** y otros **más de un
  día antes**.
- Hay **señuelos**: eventos que se ven feos pero son normales (respaldos nocturnos, cierres de nómina, cargas masivas).
  Alertar por ellos cuenta como falsa alarma.
- Los datos tienen **ruido, celdas vacías y apagones**.
- Los logs traen muchos errores que no significan nada; las pistas reales son pocas.
- El **contexto del negocio** ayuda a saber qué es normal.

---

## 3. Los datos

### Estructura

```
data/
├── gracko/ gramo/ kaiku/ ttr/      ← una corrida de ejemplo, para explorar
├── _solucion/                      ← respuestas de esa corrida (solo para autocalificarse)
└── corridas/
    ├── corrida_01 … corrida_54/    ← 54 semanas simuladas, del 8 al 14 de octubre
    └── corrida_01…10/_solucion/    ← solo las 10 primeras tienen respuestas
```

### Los 3 archivos de cada empresa

1. **`metricas.csv`**: los «signos vitales» del servidor, **una fila por minuto** (~9 200 filas). Columnas:
   - `cpu`: qué tan ocupado está el procesador (%).
   - `ram`: memoria usada (%).
   - `disco`: qué tan lleno está el disco (%).
   - `latencia_ms`: qué tan lento responde el sistema.
   - `errores`: errores por minuto.

   Trae celdas vacías que hay que limpiar.
2. **`logs.md`**: el «diario» del sistema, con 3 secciones: servidor, firewall y app. Casi todo es ruido (escaneos de
   puertos, intentos SSH bloqueados, webhooks...). Las pistas reales son líneas como `disco /data al 77%`,
   `VPN: 212 intentos fallidos` o `cpu de fs-01 al 41% sostenido`.
3. **`contexto.md`**: qué hace la empresa, su horario y sus eventos programados. Sirve para descartar señuelos.

Además, `todos_metricas.csv` junta las 4 empresas con una columna `tenant`.

---

## 4. Las 4 empresas

| Empresa | Giro | Horario | Eventos normales (señuelos) |
|---|---|---|---|
| **gracko** | Despacho contable y fiscal, 12 empleados | L–V 08–18 h, sáb 09–13 h | Respaldo diario 23:00; carga masiva vie 9, 17:00–19:30; cierre de nómina lun 12, 10:00–14:00 |
| **gramo** | Distribuidora de alimentos a restaurantes, 25 empleados | L–S 07–16 h; pedidos en línea 24/7 | Promoción 2x1 vie 9, 10:00–12:00; snapshot de inventario los sábados 03:00–04:30; picos de pedidos 07:30 y 13:00 |
| **kaiku** | Tienda en línea de café, 18 empleados | Tienda 24/7; soporte L–S 09–19 h | Campaña de correo vie 9, 12:00 (~2 h de pico); reindexado los domingos 04:00; respaldo diario 03:00 |
| **ttr** | Transporte y logística de última milla, 40 empleados | L–S 06–20 h; planeación de rutas 06–08 h | Mantenimiento de red sáb 10, 22:00–23:00 |

Ojo: según la guía del kit, gramo y ttr tienen señuelos que **no** aparecen en su contexto
(`reporte_rutas_nocturno` y `pedido_urgente`). Por eso son más difíciles.

### Incidentes reales de la corrida de ejemplo (para ilustrar la presentación)

| Empresa | Incidentes |
|---|---|
| gracko | `deriva_disco`, `acceso_masivo_vpn`, `cpu_intermitente_erp` |
| gramo | `trafico_hostil_lento`, `fuga_memoria_worker`, `agotamiento_pool_inventario` |
| kaiku | `saturacion_bd_gradual`, `fuga_conexiones_checkout`, `rafaga_bot_checkout` |
| ttr | `red_gps_intermitente`, `crecimiento_cache_gps`, `bloqueo_base_rutas` |

---

## 5. La solución del equipo

### Punto de partida: gracko

Es la empresa más clara: todos sus señuelos están en el contexto, tiene horario de oficina simple y sus 3 incidentes
son muy distintos entre sí.

| Incidente | Qué se ve en los datos | Cómo lo detectamos | Anticipación posible |
|---|---|---|---|
| **Disco llenándose** (`deriva_disco`) | El disco sube de ~58% (normal) a 63% → 68% → 76% → **92%** en dos días. El respaldo de las 23:00 del 11 de octubre falla por falta de espacio. El contexto ya advertía: «/data sin alerta de capacidad desde hace 3 meses». | El disco está muy por encima de su nivel normal y lleva horas subiendo sin bajar. | **Más de un día** |
| **Ataque a la VPN** (`acceso_masivo_vpn`) | 12 oct 23:58: `VPN: 9 intentos fallidos en 10 min`. 13 oct 00:31: `37 cuentas bloqueadas`. 00:33: `212 intentos fallidos`. | Contar intentos fallidos de VPN en los logs, sobre todo de noche. Se ignoran los «escaneos de puertos» e «intentos SSH», que son ruido diario. | ~30 minutos |
| **CPU anormal** (`cpu_intermitente_erp`) | La CPU normal es de ~20–25%. El 14 de octubre ya está en ~47% desde temprano, fuera de horario y sin respaldo. Luego aparece `cpu de fs-01 al 41% sostenido`. | CPU alta durante varios minutos, fuera de horario y fuera de la ventana del respaldo. | Horas |

### Método: línea base estadística

La propuesta del equipo se basa en **media, mediana y moda** para aprender qué es «normal» y alertar cuando algo se
aleja de eso. El nombre formal es **línea base estadística (*baseline*)**, la misma idea que usan herramientas reales
de monitoreo.

| Medida | Uso en la solución |
|---|---|
| **Mediana** ⭐ | La medida principal: no se deja engañar por picos raros ni por datos vacíos. |
| **Media + desviación estándar** | Miden qué tan lejos de lo normal está cada minuto. |
| **Moda** | Poco útil para números continuos (casi nunca se repite el mismo valor exacto). Sirve más para los logs (el mensaje más común = ruido). El equipo la evaluó y explica por qué no es la principal, lo que demuestra criterio. |

**Diferenciador:** lo normal no se calcula igual a todas horas. Se calcula **por horario** (de oficina, de noche, de
respaldo), usando el `contexto.md` de cada empresa. Así se evitan las falsas alarmas por los señuelos.

### Pasos del sistema

1. Leer las métricas **minuto a minuto, solo hacia adelante** (cumple la regla de no ver el futuro).
2. Limpiar las celdas vacías (rellenar con el valor anterior).
3. Calcular la línea base (mediana y desviación) de cada métrica.
4. Consultar la tabla de «ventanas normales» sacada del contexto.
5. Aplicar los 3 detectores (disco, VPN y CPU).
6. No repetir la misma alerta (por ejemplo, máximo una por tipo cada 12 horas).
7. Guardar `alertas.csv` y compararlo con `_solucion` para medir detectados, falsas alarmas y anticipación.
8. Probar en otras corridas (02 a 54) y después adaptar la solución a gramo, kaiku y ttr.

### Reparto del equipo

| Persona | Tarea |
|---|---|
| 1 | Carga y limpieza de datos; cálculo de la línea base |
| 2 | Detector de disco |
| 3 | Detector de VPN (logs) |
| 4 | Detector de CPU y tabla de horarios y señuelos |
| Líder | Documentación, presentación e integración final |

---

## 6. Enfoque de la presentación: comercial, no metodológico

El consejo recibido: hablar **menos de cómo funciona por dentro** y **más de por qué le importa al cliente**.

### Traducción de técnico a comercial

| ❌ Técnico | ✅ Comercial |
|---|---|
| «Calculamos la mediana y la desviación estándar del disco por ventana horaria.» | «Le avisamos al contador **un día antes** de que se llene su servidor y pierda el respaldo de sus clientes.» |
| «Filtramos los señuelos con una tabla de ventanas esperadas.» | «No lo molestamos cada noche por el respaldo. **Solo suena cuando importa.**» |
| «Contamos intentos fallidos de VPN por ventana de 10 minutos.» | «Detectamos que alguien intentaba entrar a medianoche, **antes de que bloqueara 37 cuentas**.» |

### Preguntas que debe responder la presentación

1. **¿Qué problema duele?** Las PyMEs se enteran de sus fallas cuando el cliente ya está enojado: pierden dinero,
   tiempo y reputación.
2. **¿Quién lo sufre?** Un despacho de 12 personas sin equipo de TI, que no puede vigilar su servidor las 24 horas.
3. **¿Qué ofrecemos?** Un vigilante que avisa antes, y solo cuando vale la pena.
4. **¿Qué gana el cliente?** Horas o hasta un día de anticipación, sin sustos por falsas alarmas.
5. **¿Por qué nosotros?** Entendemos el negocio de cada empresa: sabemos que un respaldo nocturno no es una emergencia.

### Estructura sugerida (7 diapositivas)

1. **Historia de apertura:** «Domingo, 11 de la noche. El respaldo del despacho falla porque el disco está lleno. Al
   día siguiente, en pleno cierre de nómina, un cliente llama furioso...» (basada en el caso real de gracko).
2. **El problema**, y por qué les pasa a muchas PyMEs.
3. **Nuestra solución**, en una frase.
4. **La misma historia, con nosotros:** «El sábado, el sistema ya había avisado. El contador liberó espacio y nadie se
   enteró del problema.»
5. **Resultados en números:** incidentes detectados, falsas alarmas evitadas y horas de anticipación (el equipo los
   tendrá al terminar el código).
6. **Cómo funciona por dentro** (una sola diapositiva y sencilla): «el sistema aprende qué es normal para cada empresa
   y avisa cuando algo se sale de lo normal». Los detalles (mediana, desviación) se guardan para las preguntas de los
   jueces.
7. **Cierre:** «Antes de que suene el teléfono, nosotros ya avisamos.»

---

## 7. Datos útiles para la presentación

- 4 empresas, 54 semanas simuladas, ~9 200 minutos por empresa y semana.
- 12 incidentes reales por corrida (3 por empresa) contra más de 10 señuelos.
- gracko: el disco pasa de 58% a 92% en ~2 días; el ataque a la VPN escala de 9 a 212 intentos fallidos en ~35
  minutos y bloquea 37 cuentas.
- Los resultados finales (porcentaje de detección, falsas alarmas y anticipación promedio) están **pendientes**: los
  aportará el equipo cuando termine el código. No los inventes; deja espacios marcados como `[PENDIENTE]`.

---

## 8. Qué se necesita de ti

1. Generar la **documentación** de la solución: clara, corta y comercial.
2. Generar el **contenido de la presentación** (texto por diapositiva y notas de lo que se dice), siguiendo la
   estructura de la sección 6.
3. Mantener el tono **comercial**: el valor para el cliente va primero y la técnica, después y breve.
4. Preparar un **apartado de preguntas y respuestas** para los jueces (por ejemplo, «¿cómo evitan las falsas
   alarmas?», «¿por qué la mediana y no la media?», «¿cómo cumplen la regla de no ver el futuro?»).
5. Escribir en **español** y en un lenguaje sencillo.
6. No inventar resultados numéricos: marcar como `[PENDIENTE]` lo que todavía no se ha medido.
