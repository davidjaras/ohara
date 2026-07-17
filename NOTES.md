# NOTES — decisiones de diseño y lecciones

## Logo inicial: O circular abierta
La apertura queda centrada a la 1:30, mide 50° y usa un trazo constante de 7
unidades sobre un viewBox de 64. `currentColor` es canónico para controlar las
variantes desde CSS sin duplicar geometría. Los rasterizados se aplazaron
deliberadamente.

## Auth: sistema nativo de Django, páginas server-rendered
Login/logout/cambio/reset de password usan `django.contrib.auth.urls` con
templates propios (CSS inline a juego con el tema). La SPA usa la sesión de
Django (SessionAuthentication de DRF + CSRF token) y redirige a
`/accounts/login/` ante 401/403. Sin OAuth ni JWT: para una app personal el
auth de sesión nativo es lo más simple y estándar.

## Multiusuario: FK a User en todo, backfill en la migración
`Session/ActiveTimer/Measurement/WeeklyGoal` llevan FK a User y las
constraints de unicidad son por usuario. La migración 0002 crea al dueño
(`davidjaras`, staff+superuser, contraseña inutilizable hasta
`changepassword`) y le asigna todas las filas existentes: cero datos
perdidos. Los services reciben `user` como primer argumento; las vistas
filtran por `request.user`.

## i18n en dos capas
Frontend: react-i18next con diccionarios en `src/lib/i18n.ts` (es default,
en), elección persistida en localStorage y selector en Ajustes. Backend:
mensajes de error con gettext (fuente en inglés, catálogo es en
`backend/locale`); la API traduce según `Accept-Language`, que el cliente
manda con el idioma activo.

## Acumulado semanal calculado en el backend
`week_cumulative` devuelve lunes→hoy (nunca días futuros: extender la línea
plana hasta el domingo sería engañoso). El frontend solo rellena el eje hasta
el domingo con puntos nulos para que la semana completa sea visible.

## Chulito de la gráfica semanal: shape custom, no LabelList
El `LabelList` de recharts v3 con `content` custom solo renderizaba una parte
de las entradas (capa vacía / índices parciales). El check sobre las barras
cumplidas se dibuja en un `shape` custom del `Bar`, que recibe `payload` y
posición de forma determinista. Lección: en recharts v3, para adornos por
barra, `shape` es más confiable que `LabelList`.

## Rangos de las gráficas
Semanal: 4/12/26/52 semanas (default 12: un trimestre se lee de un vistazo).
Peso: 1m/3m/1año/todo (default 3m), filtrado client-side porque el volumen de
mediciones personales es trivial. El acumulado es fijo a la semana en curso
por diseño.

## CSRF con Vite en desarrollo
El proxy de Vite (`changeOrigin: true`) hace que Django vea Host
`127.0.0.1:8000` con Origin `localhost:5173` y rechace el POST. Fix estándar:
`CSRF_TRUSTED_ORIGINS` con los orígenes de Vite solo en DEBUG.

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
