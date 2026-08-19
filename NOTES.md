# NOTES — decisiones de diseño y lecciones

## Logo inicial: O circular abierta
La apertura queda centrada a la 1:30, mide 50° y usa un trazo constante de 7
unidades sobre un viewBox de 64. `currentColor` es canónico para controlar las
variantes desde CSS sin duplicar geometría. Los rasterizados se aplazaron
deliberadamente.

Corrección de color contra la imagen de referencia: la geometría del canon ya
calcaba el ejemplo (stroke/diámetro 0.150 vs 0.149; apertura en la misma
zona), pero el `#22C55E` del draft es más saturado que el verde del ejemplo
(mismo hue ~142°, más suave). El emerald del brand pasó a `#4FC580` (aplanado
del degradado de referencia) para exports/favicon; dentro de la app el símbolo
usa `currentColor` y toma el acento de la UI (header y páginas de auth), así
nunca desentona con los botones.

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

## Sesión que cruza medianoche: se parte por día
Antes se atribuía entera al día en que empezó. Se cambió: una sesión de 23:30
a 00:30 aporta 30 minutos a cada día. La fila sigue teniendo un solo `date`
(el día de inicio, que ordena el historial); el reparto se calcula al agregar,
en `services.day_segments`. Así no hay modelo nuevo, ni migración, y las
sesiones ya guardadas quedan bien atribuidas retroactivamente porque ya tenían
`started_at`/`ended_at`. También parte entre semanas la sesión que va de
domingo a lunes.

El costo es que `daily_minutes` y `_week_seconds` dejan de agregar en SQL y
expanden segmentos en Python. A escala personal es irrelevante, y a cambio la
agregación y la validación del tope diario comparten exactamente el mismo
cálculo, así que nunca discrepan.

**Reparto proporcional, no por reloj de pared.** `duration_seconds` excluye las
pausas, así que no coincide con `ended_at - started_at` y no se puede rebanar
el intervalo directamente. Cada día recibe su fracción del tiempo de pared, y
el residuo del redondeo va al último día para que las partes sumen exacto.
Dónde cayeron las pausas no se guarda; repartirlas parejo es la regla simple
más justa.

## Tope de 1440 minutos por día
Un día no puede tener más minutos de los que tiene. `MAX_DAY_MINUTES` /
`MAX_WEEK_MINUTES` viven en settings y se validan en el serializer (respuesta
rápida) y en el servicio (la regla real): cada registro ≤ 1440 y la suma del
día ≤ 1440, contando el tiempo que se derramó de una sesión del día anterior.
Al editar, la propia fila se excluye del total usado.

Límite conocido: el tope por día se valida en las escrituras manuales. Una
sesión cronometrada podría, combinada con registros manuales del mismo día,
pasarse. Rechazarla al finalizar significaría tirar tiempo real ya vivido, así
que no se hace. Lo que sí se acota es el cronómetro olvidado: `finish_timer`
recorta a 24 h desde el inicio en vez de escribir una sesión imposible.

## Editar registros, no solo crear y borrar
`PATCH /api/sessions/<id>/` con campos parciales. Reescribir la fecha o la
duración de una sesión cronometrada vuelve mentira sus marcas de tiempo, así
que se borran y la fila pasa a ser un registro manual corregido, que es lo que
realmente es. Editar solo la nota las conserva.

## Sesiones con duración pactada y cierre automático perezoso
Olvidar detener el cronómetro es un fallo de memoria prospectiva, no de
disciplina: el diseño hace innecesario recordar y barato reparar. Al iniciar
se pacta una duración (presets 25/50/90, personalizada, o sin límite
explícito); la última elegida se recuerda en localStorage como el bloque
habitual.

**Finalización perezosa, sin cron ni workers.** `finalize_expired_timer` corre
al inicio de toda vista que pueda observar un cronómetro (estado, pause/resume,
start, checkin, finish, lista de sesiones, stats) y decide solo con timestamps
persistidos: quien vuelve una semana después encuentra la sesión ya cerrada y
truncada en su primer request. La pactada cierra exacto en la duración pactada
tras una gracia corta (`TIMER_GRACE_SECONDS`); la sin límite cierra tras dos
intervalos de recordatorio sin respuesta (`reminder_interval_seconds`,
congelado al iniciar desde `UserPreference.reminder_minutes`), truncada a la
última interacción confirmada — nunca al umbral: subestimar gana a inflar.

**Interacción confirmada** es toda acción mutante del usuario (start, pause,
resume, extend, checkin); un GET de estado jamás, porque la finalización
perezosa viaja en los GET y una carga pasiva del dashboard no es evidencia de
estudio. Un cronómetro en pausa nunca expira: en pausa no acumula nada, así
que no puede inflar ningún registro; solo espera.

**Reparar en vez de cancelar.** El cierre automático deja `close_reason`,
la estimación congelada (`estimated_duration_seconds`), el umbral que lo
produjo (`idle_threshold_seconds`) y queda pendiente de revisión hasta
`reviewed_at` (`needs_review` es derivado, no columna). El dashboard lo
presenta en un banner: confirmar en un toque, ajustar el fin conservando el
inicio real, o descartar. Esos campos permiten calibrar después con datos
reales: frecuencia del olvido, tamaño del ajuste y si el umbral por defecto
está mal puesto — sin construir analítica todavía.

Un extend o un pause que llegan *después* del plazo no reviven el cronómetro:
el servidor cierra primero y responde 409; el cliente refetchea y cae en el
banner. La excepción deliberada es extend dentro del flujo normal: la UI solo
lo ofrece durante la gracia, cuesta una acción y pesa lo mismo que finalizar,
porque una meta de duración no debe volverse techo. Las notificaciones del
navegador son refuerzo puro (una por fase, permiso pedido al guardar el
recordatorio en ajustes); la corrección del dato nunca depende de ellas.

## Activar un programa es empezar un plan con fechas

Hasta ahora "activar" era una etiqueta: `TrainingProfile.active_variant` decía
*qué* programa habías elegido y nada decía *desde cuándo* ni *hasta cuándo*.
Ninguna pantalla sabía en qué fase, semana o día estabas, así que todas se lo
preguntaban al usuario. `ProgramRun` (usuario, variante, `started_on`, estado)
convierte esa elección en un compromiso con fechas reales, y pasa a ser la
única fuente de verdad: `active_variant` se eliminó en vez de quedar como
columna muerta, y el endpoint del perfil sigue devolviéndola derivada del run
para no romper a nadie.

**Anclaje al lunes.** Los cinco programas nombran sus días `MONDAY`..`SATURDAY`
(nunca domingo) en el 100 % de las filas, y el resto de Ohara ya cuenta semanas
ISO. Un run empieza siempre en un lunes — cualquier fecha se ajusta hacia atrás
a su lunes, en el cliente y en el servidor — y cada día cae en el día de la
semana que escribió el coach. La posición absoluta de una semana se calcula
enumerando las semanas que existen, no sumando `Phase.weeks_count`: Glute Coach
sintetiza las suyas y los dos números podrían separarse.

**Las fechas no se mueven.** Faltar a un entrenamiento nunca corre el
calendario: la semana 3 empieza en su fecha se haya hecho o no la 2, los días
sin registrar quedan pendientes y lo que se muestra es la adherencia
(`Semana 2 · 3/5`). Extender el plan automáticamente al primer fallo convierte
la fecha de fin en una promesa que se renegocia sola; es más honesto que el
plan aguante y el número diga la verdad. El día activo del dashboard es el de
hoy si está pendiente, si no el más atrasado *de la semana en curso* — ponerse
al día el miércoles con lo del martes es normal, arrastrar la semana 1 durante
dieciséis no.

**Fuera de plan se registra igual.** Un día de otro programa, o de una semana
muy posterior, se puede registrar: la sesión queda con `run = null`, marcada
"fuera de plan", fuera de la adherencia y dentro del historial. Bloquearlo
solo obligaría a mentirle a la app para poder entrenar.

**Un día, una sesión.** `WorkoutSession` era creada sin comprobar nada en el
primer set de cada visita, así que reabrir un entrenamiento lo duplicaba —
había cuatro filas para el 2026-08-04 en la base de desarrollo. La restricción
`uniq_run_day` más un `get_or_create` lo cierran; Postgres trata los NULL como
distintos, así que las sesiones fuera de plan siguen sin restricción, que es
justo lo que se quiere. La migración de datos fusiona los duplicados que ya
existían en la sesión más completa.

**El día viaja con lo registrado.** `GET /api/training/days/<pk>/` devolvía la
prescripción y nada más, así que reabrir un día terminado pintaba un formulario
en blanco: el cliente no tenía forma de pedir su sesión. Ahora el mismo payload
trae la sesión con sus logs, la fecha agendada y, por slot, la última vez que
se hizo ese ejercicio — una consulta por ejercicio del día, no una por serie.

**"Última vez" excluye la sesión abierta**, o la línea repetiría lo que acabas
de escribir. El peso de la última vez es *placeholder*, nunca valor precargado:
las reps sí se precargan con el objetivo del coach, pero marcar una serie no
puede registrar una carga que nadie eligió. Las filas importadas no tienen
fecha, y como Postgres ordena los NULL primero en `DESC`, todo el orden por
`performed_on` va con `nulls_last`: sin eso un registro de 2023 sin fecha
aparecía como "la última vez" por encima del entrenamiento de ayer.

## El ejercicio sustituido es *el* ejercicio

Sustituir dejaba el ejercicio prescrito como título de la tarjeta y mandaba lo
que ibas a hacer de verdad a una línea pequeña debajo ("Sustituido por X").
Está al revés: si cambiaste el ejercicio, el que haces es el que manda. Ahora
el título es el sustituto — con su letra — y la prescripción queda debajo como
`en lugar de <nombre>`, que sigue siendo información útil (es lo que pidió el
programa) pero no es lo que estás levantando.

El cambio de presentación no se sostenía solo, porque destapaba dos cosas:

**La sustitución no viajaba con el día.** `days/<pk>/` no la devolvía y el
cliente solo se enteraba al abrir el selector, así que un F5 volvía a mostrar
el nombre prescrito. Con el sustituto de título eso habría sido peor que
antes: recargar deshacía el cambio a la vista. El día ahora resuelve las
sustituciones vigentes de todos sus slots en una sola consulta y las manda en
el mismo payload, junto con la `last_performance` del ejercicio **realizado** —
el historial sigue al ejercicio, no a la prescripción.

**`scope` se guardaba y luego se ignoraba.** Tanto el selector como el registro
resolvían con `filter(user, slot).order_by("-created_at").first()`, así que una
sustitución hecha como "Solo esta sesión" se aplicaba a todas las sesiones para
siempre. Con la etiqueta pequeña era un detalle; con el sustituto de título, un
cambio puntual renombraba ese slot en todas las semanas del plan.
`services.active_substitutions` es ahora el único sitio donde se resuelve —
lo leen la vista del día, el selector y el endpoint de registro — y respeta el
scope: `program` aplica a todas las sesiones del slot, `session` solo dentro de
la suya. Que sea uno solo importa: lo que muestra la tarjeta y lo que se
escribe en `SetLog.performed_exercise` salen de la misma consulta y no pueden
divergir.

**"Solo esta sesión" necesita una sesión.** Cambiar el ejercicio *antes* de
registrar la primera serie es el orden normal, y hasta ahora eso creaba la fila
con `session = None`. Ignorando el scope daba igual; respetándolo, esa fila no
coincide con nada y la sustitución no haría nada en silencio. El endpoint abre
la sesión del día (con el `get_or_create` que ya es idempotente por día) cuando
el scope es `session` y no llega ninguna.

Sigue sin haber forma de deshacer una sustitución. Con el scope respetado un
cambio de sesión se apaga solo, pero uno de programa encabeza ese slot hasta
el final del plan: hace falta un DELETE, y es el siguiente paso.

## Liquid glass: el material vive en tokens, no en componentes

Toda la UI era la misma `Card` de shadcn repetida en cada bloque de cada
pantalla. Cuando todo tiene la misma elevación, nada señala qué importa: en el
panel el cronómetro pesaba lo mismo que la lista de semanas de hace dos meses.

El material nuevo son cuatro utilidades en `index.css`, no estilos por
componente: `glass-subtle` (relleno + borde, sin `backdrop-filter`),
`glass-elevated` (el panel estándar), `glass-hero` (el foco de la pantalla) y
`glass-overlay` (lo que flota sobre contenido que scrollea). Solo las tres
últimas llevan `backdrop-filter` y una pantalla debe tener pocas: apilar capas
desenfocadas es lo que vuelve caro este material en Safari móvil. Las filas y
los chips usan `glass-subtle`, que no cuesta nada.

**La capa ambiental no es decoración.** Sin color detrás, `backdrop-filter` no
tiene nada que desenfocar y los paneles se leen como tarjetas grises planas —
exactamente el problema del que veníamos. Está hecha con `radial-gradient` y no
con `filter: blur()` sobre un círculo sólido: se ve igual y evita que el
compositor rasterice una capa grande en cada pintado.

**El acento sigue siendo `--primary`, y solo `--primary`.** Los campos
ambientales se derivan con `color-mix(in oklab, var(--primary) 42%, transparent)`,
así que los siete bloques `[data-accent]` quedaron intactos: definen `--primary`
y el vidrio los sigue solo. Sin variantes nuevas por acento, sin `--accent-rgb`.

**La regla de composición: el panel es la excepción.** El contenedor por
defecto es una `Section` — etiqueta, filete, contenido directo sobre la página.
Un panel significa "esto está por encima del resto", y se reserva para el
cronómetro, el aviso de sesión por revisar, el plan en curso y las superseries
del día de entreno, donde "estos dos ejercicios son una unidad" es todo el
punto. Diez tarjetas entre Peso y Ajustes pasaron a diez secciones.

**Lo que no se tocó, a propósito.** La tabla de series del día de entreno
(`TABLE_GRID`) está afinada al rem para un teléfono; cambiar la altura de un
input o el tamaño de fuente ahí rompe la fila. Solo cambió el cromo alrededor.

`--nav-offset` existe porque el nav flota: las páginas y el temporizador de
descanso reservan el mismo valor en vez de dos paddings elegidos a ojo.

## Un slot es de una semana, no del programa

`scope='program'` se guardaba, se respetaba… y aun así el ejercicio original
volvía cada semana. El fallo no estaba en el scope sino en el modelo mental:
`ExerciseSlot` cuelga de `WorkoutDay`, que cuelga de `Week`, y el cargador
re-materializa la lista de días de la fase **dentro** del bucle de semanas. La
semana 1 y la semana 2 de la misma fase son filas distintas con PKs distintos.
`active_substitutions` filtraba `slot__in=slots` antes de aplicar el `Q` del
scope, así que `program` significaba en realidad "todas las sesiones de esta
semana". El comentario de `ExerciseSubstitution` afirmaba que el slot era
"global (part of the program)"; nunca lo fue.

**La clave es (variante, day.order, slot.order, ejercicio)**, en
`services.sibling_slot_map`, y el ejercicio no sobra. Medido sobre la base real:
dentro de una fase, las 609 posiciones prescriben el mismo ejercicio en todas
sus semanas, así que exigir el ejercicio no cuesta ni una coincidencia. Entre
fases es al revés: 37 de 39 posiciones se reutilizan y solo **1** conserva el
ejercicio — la fase 2 pone otro press en `día 1 / slot 1`. Emparejar solo por
posición habría cambiado en silencio ejercicios que nadie pidió cambiar. Así
que un cambio "de programa" viaja por todas las semanas de su fase siempre, y
salta de fase únicamente donde el programa vuelve a prescribir ese ejercicio en
esa posición.

`ExerciseSubstitution.original_exercise` guarda lo que se sustituyó en el
momento de escribirlo. Es la mitad de la clave, y es lo que lee la etiqueta
"en lugar de X": resuelta desde otra semana, la fila `slot` ya no es la que
tienes delante.

`active_substitutions` sigue siendo el único sitio donde se resuelve, con la
misma firma y la misma forma de retorno, así que la tarjeta y
`SetLog.performed_exercise` siguen saliendo de la misma consulta. La vista del
día construye el mapa una vez y se lo pasa a los dos consumidores; el coste es
+3 consultas constantes sobre el día, sin cambiar la pendiente (que sigue
siendo +1 por ejercicio, de `last_performances`, y es anterior a esto).

**Ningún test lo veía** porque `build_program` venía por defecto con
`weeks=1`: todas las pruebas de sustitución corrían contra un árbol de un solo
slot, donde `ExerciseSlot.objects.get()` funciona precisamente porque no hay
nada más. El fixture `multiweek_program` (2 fases × 3 semanas, con ejercicio
propio por fase) es la forma mínima en la que el fallo se puede reproducir.

**Deshacer ya existe** (`DELETE /api/training/slots/<pk>/substitutions/`), que
era el paso pendiente que dejaba la nota anterior. Borra lo que
`active_substitutions` resuelve para ese slot, no lo que apunte a esa fila: así
deshaces lo que estabas viendo, y quitar un cambio de sesión destapa el de
programa que había debajo en vez de llevárselo por delante.

**`last_performed_exercise` es para el cambio que nunca registraste.** Si
sustituiste "solo esta sesión" hace meses y desde entonces repites el sustituto
a mano, la tarjeta lo dice — *"la última vez hiciste X"* — y al tocarlo abre el
selector con X ya elegido y scope de programa. No retitula la tarjeta sola:
mientras no elijas, el título sigue siendo la prescripción, que es lo que
mantiene de acuerdo lo que ves y lo que se escribe al registrar una serie. Es
un campo distinto de `last_performance`, que va indexado por ejercicio
realizado y trae las series; este solo responde "aquí llevas tiempo haciendo
otra cosa".
