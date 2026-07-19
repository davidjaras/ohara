<p align="center">
  <img src="frontend/public/brand/ohara-symbol-emerald.svg" alt="Ohara" width="72">
</p>

# ohara

App personal para trackear tiempo de estudio, inspirada en el modelo de metas
semanales de Garmin: meta semanal en minutos, gráficas por día y por semana,
chulito verde en las semanas cumplidas y racha de semanas consecutivas.

- **Backend:** Django 6 + Django REST Framework + PostgreSQL (API-first,
  multiusuario con el auth nativo de Django).
- **Frontend:** React 19 + Vite + Tailwind v4 + shadcn/ui (tema oscuro, acento
  esmeralda), interfaz en español e inglés (react-i18next).

## Desarrollo

Requisito único: [Docker](https://docs.docker.com/get-docker/) (con Compose).

```bash
docker compose up
```

Eso levanta los tres servicios:

- **Frontend:** http://localhost:5173/ (Vite con hot-reload; proxy de `/api`,
  `/accounts` y `/admin` al backend)
- **API:** http://localhost:8000/api/
- **Postgres 17:** puerto `5432` publicado al host; los datos persisten en el
  volumen `pgdata` (sobreviven a `docker compose down`; solo se borran con
  `docker compose down -v`).

Las migraciones corren solas al arrancar el backend. El código de `backend/` y
`frontend/` está montado como volumen, así que los cambios se reflejan sin
rebuild; solo hace falta `docker compose build backend` si cambiás
dependencias del backend (`pyproject.toml`).

La app requiere login (`/accounts/login/`). El primer usuario sale de la
sección siguiente.

### Superusuario, admin y consola de Django

Con el compose corriendo:

```bash
# Crear un superusuario (pide username, email y contraseña):
docker compose exec backend uv run python manage.py createsuperuser

# Cambiar la contraseña de un usuario existente:
docker compose exec backend uv run python manage.py changepassword <usuario>

# Migraciones:
docker compose exec backend uv run python manage.py makemigrations
docker compose exec backend uv run python manage.py migrate

# Consola interactiva de Django:
docker compose exec backend uv run python manage.py shell
```

- **Admin:** http://localhost:5173/admin/ — requiere un usuario con
  `is_staff`. Los modelos del tracker (Session, ActiveTimer, Measurement,
  WeeklyGoal) están registrados.
- **Login de la app:** http://localhost:5173/accounts/login/. Cambio de
  contraseña en `/accounts/password_change/`; reset en
  `/accounts/password_reset/` (en desarrollo el email se imprime en los logs
  del backend: `docker compose logs -f backend`).

### Tests

```bash
docker compose exec backend uv run pytest
```

También corren desde el host si tenés [uv](https://docs.astral.sh/uv/): con el
compose arriba, `cd backend && uv run pytest` (usa el Postgres del compose por
el puerto publicado). En CI (GitHub Actions) la suite corre contra un service
container de Postgres en cada push/PR a `main`.

Cubren la lógica de negocio (agregación diaria/semanal, acumulado de la semana
en curso, meta cumplida, racha, cronómetro con pausas), el flujo de registro
vía API y la separación de datos entre usuarios.

### Settings

`backend/config/settings/` es un paquete con tres módulos:

- `base.py` — todo lo compartido; la DB se lee de **`DATABASE_URL`**.
- `dev.py` — DEBUG, secret con default, CSRF para Vite, email por consola.
  Default de `manage.py` y del compose.
- `prod.py` — exige `OHARA_SECRET_KEY`, cookies secure, header de proxy SSL.
  Default de `wsgi.py`/`asgi.py` y fijado en la imagen de producción.

### Estructura

```
backend/
  config/
    settings/        # base.py / dev.py / prod.py
  tracker/
    metrics.py       # registro de métricas en código (ver Extensibilidad)
    models.py        # Session, ActiveTimer, Measurement, WeeklyGoal
    services.py      # lógica de negocio (recibe now/today explícitos)
    views.py         # API REST
    tests/
frontend/
  src/
    lib/api.ts       # cliente tipado de la API
    components/      # layout, timer, charts, ui/ (shadcn)
    pages/           # dashboard, historial, peso, ajustes
Dockerfile           # multi-stage: target dev (compose) y prod (Railway)
docker-compose.yml   # desarrollo local: db + backend + frontend
docs/brand.md        # marca: símbolo, colores, usos (preview en /brand-preview)
NOTES.md             # decisiones de diseño
```

### API (resumen)

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/metrics/` | Métricas registradas |
| GET/DELETE | `/api/timer/?metric=` | Estado / descarte del cronómetro |
| POST | `/api/timer/{start,pause,resume}/` | Acciones del cronómetro |
| POST | `/api/timer/finish/` | Finalizar y guardar sesión (con nota) |
| GET/POST | `/api/sessions/` | Listar / registrar manualmente sesiones |
| DELETE | `/api/sessions/<id>/` | Borrar sesión |
| GET/POST | `/api/measurements/?metric=` | Mediciones (ej. peso) |
| DELETE | `/api/measurements/<id>/` | Borrar medición |
| GET/PUT | `/api/goal/?metric=` | Meta semanal (aplica desde la semana actual) |
| GET | `/api/stats/?metric=&weeks=` | Payload del dashboard (incluye acumulado semanal) |
| GET | `/api/me/` | Usuario autenticado |

Toda la API requiere sesión autenticada (auth de sesión de Django + CSRF);
cada usuario ve solo sus propios datos.

### Extensibilidad

Las métricas viven en `backend/tracker/metrics.py`, un dict en código con dos
clases: `session` (eventos con duración, meta y racha — ej. estudio) y
`measurement` (valor puntual en una fecha — ej. peso). Agregar una métrica
nueva es **una entrada en ese dict más su UI**; las filas existentes
referencian la métrica por clave de texto, así que no hay migración de datos.
Peso se agregó exactamente así, sin tocar modelos ni vistas.

## Deploy (Railway)

Un solo servicio: la imagen de producción (target `prod` del `Dockerfile`)
compila el frontend, lo sirve con WhiteNoise desde Django, y **corre las
migraciones automáticamente en cada arranque** antes de levantar gunicorn en
`$PORT`. La base es el plugin de Postgres de Railway, conectado vía
`DATABASE_URL`.

Variables de entorno del servicio:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | referencia al Postgres de Railway (`${{Postgres.DATABASE_URL}}`) |
| `OHARA_SECRET_KEY` | generar: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `OHARA_ALLOWED_HOSTS` | el dominio del servicio (ej. `ohara-production.up.railway.app`) |
| `OHARA_CSRF_TRUSTED_ORIGINS` | el mismo dominio con esquema (`https://…`) |
| `OHARA_TIME_ZONE` | ej. `America/Bogota` |

Deploy continuo: Railway buildea el `Dockerfile` de la raíz en cada push a
`main`. El gate de tests es el workflow de GitHub Actions
(`.github/workflows/ci.yml`).

Primer usuario en producción (desde Railway → servicio → terminal, o con
`railway run`):

```bash
uv run python manage.py createsuperuser
```

Nota: el reset de contraseña por email requiere configurar SMTP (variables
`EMAIL_*` de Django); si no, usá `changepassword` por consola.
