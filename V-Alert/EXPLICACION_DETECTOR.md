# Cómo anticipamos los incidentes de Gracko

> Explicación técnica del detector, sin necesidad de saber programar.

## 1. El reto en una frase

Gracko (despacho contable, 12 empleados) tiene problemas de TI y se entera **cuando el cliente llama enojado**. Nuestro detector revisa sus datos minuto a minuto y avisa **antes** de esa llamada, sin dar falsas alarmas.

## 2. Qué datos usamos

| Fuente | Qué contiene | Para qué la usamos |
|---|---|---|
| `metricas.csv` | Una fila por minuto: CPU, RAM, disco, latencia y errores | Detectar tendencias (algo que sube poco a poco) |
| `logs.md` | Mensajes del servidor, firewall y aplicación | Contar intentos fallidos de conexión VPN |
| `contexto.md` | Horarios de oficina, respaldos y eventos del negocio | Saber qué es **normal** y no confundirlo con un problema |

**Regla de oro:** en cada minuto el detector solo mira el pasado, nunca datos del futuro (así lo exige el reto).

## 3. Las ideas clave (aplican a todas las reglas)

### 3.1 Promedios en lugar de valores sueltos
Los datos tienen **ruido**: un minuto la CPU marca 24%, el siguiente 31% y el siguiente 25%. Si reaccionáramos a cada salto, avisaríamos todo el tiempo.
Por eso trabajamos con **promedios móviles**: el promedio de los últimos 5, 30 o 60 minutos. Es como mirar la tendencia del clima de la semana en vez de la temperatura de un solo instante.

### 3.2 Tendencia: "sube y no baja"
Un problema real suele **crecer poco a poco**. Comparamos el promedio de ahora con el de hace 30, 60 y 90 minutos:

```
hace 90 min  <  hace 60 min  <  hace 30 min  <  ahora   →  tendencia en aumento
```

Si sube en los cuatro puntos, no es casualidad: algo se está acumulando.

### 3.3 Señuelos: lo que se ve feo pero es normal
Antes de avisar revisamos si el comportamiento tiene una explicación del negocio (según `contexto.md`):

| Señuelo | Cuándo | Por qué se ignora |
|---|---|---|
| Horario de oficina | L–V 08:00–18:00, sáb 09:00–13:00 | Los empleados usan el sistema, es carga normal |
| Respaldo nocturno | Diario 23:00–23:45 | Copia de archivos al NAS; sube la CPU ~14 puntos |
| Carga masiva de declaraciones | Vie 9-oct, 17:00–19:30 | Evento planeado |
| Cierre de nómina | Lun 12-oct, 10:00–14:00 | Evento planeado |

> El respaldo termina a las 23:40, pero le dimos **5 minutos extra** porque el promedio de CPU tarda un poco en bajar.

### 3.4 Datos faltantes (apagones)
Hay minutos con celdas vacías. Si faltan **hasta 3 minutos**, usamos el último valor conocido. Si falta más (un apagón), **no inventamos datos**: dejamos el hueco vacío.
Esto corrigió una falsa alarma real: durante un apagón de 15 minutos, el sistema "congelaba" la CPU del respaldo (42%) y parecía un problema.

### 3.5 Un solo aviso por incidente
Si el problema sigue presente, **no repetimos el aviso**. Solo avisamos de nuevo si el problema desaparece por más de 12 horas. Así cada incidente genera exactamente una alerta.

## 4. Las cuatro reglas de detección

### Regla 1: Disco `/data` en riesgo
- **Qué vigila:** el promedio de uso del disco en los últimos 30 minutos.
- **Avisa si:** está entre **60% y 70%** y lleva **90 minutos subiendo sin bajar**.
- **Por qué funciona:** el disco normal se mantiene estable en ~58%. Cuando empieza a llenarse, sube de forma constante durante días. Lo atrapamos en cuanto cruza el 60%, mucho antes de que llegue al 100%.
- **Pista del contexto:** "`/data` sin alerta de capacidad desde hace 3 meses".

### Regla 2: CPU elevada
- **Qué vigila:** el promedio de CPU de los últimos 5 minutos.
- **Avisa si:** supera el **40%** fuera del horario de oficina, fuera del respaldo y fuera de los eventos del negocio.
- **Por qué funciona:** de noche nadie usa el sistema; si la CPU sube sin motivo, algo anda mal. El incidente real ocurre en horario de oficina (14-oct 09:20), pero **la noche anterior** ya da señales y ahí lo atrapamos.

### Regla 3: Ataque VPN (aviso temprano por errores)
- **Qué vigila:** el promedio de **errores por minuto** de la última hora.
- **Avisa si se cumple todo esto:**
  1. los errores son **≥ 0.5 por minuto** (lo normal es ~0.2);
  2. **suben sin parar** durante 90 minutos;
  3. CPU, disco y latencia están **normales**, y no hubo picos de CPU ≥ 45% en las últimas 2 horas;
  4. es **fuera de oficina**.
- **Por qué funciona:** unas 3 horas antes del ataque, los errores empiezan a crecer poco a poco mientras todo lo demás está tranquilo. Si nada explica esos errores, lo más probable es que alguien esté intentando entrar.
- **Por qué los filtros:** el disco lleno y el problema de CPU también generan errores. Al exigir que todo lo demás esté normal, evitamos confundirlos.

### Regla 4: Ataque VPN (confirmación en los logs)
- **Qué vigila:** los mensajes de VPN con intentos fallidos en `logs.md`.
- **Avisa si:** hay **más de 12 intentos fallidos en 35 minutos de madrugada** (00:00–06:00).
- **Por qué más de 12:** en los logs hay un señuelo: el usuario "contador" falla 9 veces (seguramente olvidó su contraseña). El ataque real son **212 intentos** desde una red externa (`203.0.113.0/24`).
- **Rol:** es la red de seguridad. Si la Regla 3 no alcanzó a avisar, esta lo detecta.

## 5. Resultados

Probamos el detector en las **54 corridas** del dataset. Calificamos con las 10 que traen la solución oficial (la solución **solo** se usó para calificar, nunca para detectar).

| Incidente real | Detectado | Anticipación |
|---|---|---|
| Disco se llena (11-oct 23:00) | 10/10 | **~49 horas antes** |
| Ataque VPN (13-oct 00:30) | 10/10 | **~2 horas antes** (de 1.6 a 2.6 h) |
| CPU intermitente del ERP (14-oct 09:20) | 10/10 | **~14 horas antes** |

- **Incidentes detectados:** 30 de 30
- **Falsas alarmas:** 0
- **Avisos por corrida:** exactamente 3 (uno por incidente)

## 6. Límites honestos

1. **VPN con 1 día de anticipación no fue posible.** Revisamos firewall, logs y métricas: antes de las ~21:00 del día del ataque no hay ninguna señal distinta a lo normal.
2. **Riesgo de "aprenderse el examen".** Algunos números (0.5 errores/min, 45% de CPU) los ajustamos mirando estas mismas corridas. Con datos nuevos podría funcionar un poco peor. Por eso la Regla 4 sigue activa como respaldo.
3. **El aviso del disco llega muy temprano (~49 h).** Si el jurado solo acepta avisos dentro de cierta ventana de tiempo, podría contarlo como falsa alarma.
4. **Los eventos del negocio están escritos a mano** a partir de `contexto.md`. Con otra empresa habría que actualizarlos.
