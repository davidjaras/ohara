# NOTES — decisiones de diseño y lecciones

## Semana ISO (lunes-domingo)
Todas las agregaciones semanales, la meta y la racha usan semana ISO. Es el
estándar y coincide con el uso cotidiano local.

## Extensibilidad = registro en código, no esquema dinámico
`tracker/metrics.py` es un dict de métricas con dos clases: `session` (eventos
con duración, meta semanal, racha) y `measurement` (valor puntual en una
fecha). Los modelos referencian la métrica por clave de texto, así que agregar
una métrica nueva es una entrada en el dict + UI; cero migración de datos.
Se descartó una tabla de definiciones de métricas: para un solo usuario es
sobreingeniería.

## Meta semanal con snapshot histórico
`WeeklyGoal(metric, week_start, minutes)`: cambiar la meta escribe la fila de
la semana actual y las semanas pasadas se evalúan con la meta que regía
entonces. Evita que subir la meta te "rompa" retroactivamente rachas ya
ganadas (mismo comportamiento que Garmin).

## Cronómetro persistido en el backend
`ActiveTimer` guarda `started_at`, `accumulated_seconds` y `running_since`
(null = pausado). El tiempo transcurrido se calcula, no se cuenta con ticks:
un refresh, cierre del navegador o reinicio del servidor no pierden nada.
A lo sumo un timer por métrica (unique).

## `now`/`today` como parámetros explícitos en services
Toda la lógica de negocio recibe el tiempo como argumento; solo las vistas
llaman `timezone.now()`. Los tests de lógica no necesitan mocks (solo los de
API mockean el now de la vista).

## Minutos: sumar segundos primero, redondear después
Las duraciones se guardan en segundos; los agregados suman segundos y recién
al final hacen `// 60`. Evita perder minutos por redondeo por sesión. La meta
se compara en segundos (`total_seconds >= goal * 60`).

## Resultado del ejercicio de extensibilidad (peso)
Agregar "peso" (métrica tipo medición) requirió en el backend exactamente una
entrada en `METRICS` — cero cambios de modelos, migraciones o vistas — más su
página en el frontend y tests. El núcleo (timer, agregaciones, meta, racha) no
se tocó, que era el criterio de que el diseño estaba bien.

## Sesión que cruza medianoche
Se atribuye al día local en que empezó (comportamiento Garmin). Simple y
predecible; no se parte en dos.
