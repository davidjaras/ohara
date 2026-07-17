<p align="center">
  <img src="frontend/public/brand/ohara-symbol-emerald.svg" alt="Ohara" width="72">
</p>

# ohara

App personal para trackear tiempo de estudio, inspirada en el modelo de metas
semanales de Garmin: meta semanal en minutos, gráficas por día y por semana,
chulito verde en las semanas cumplidas y racha de semanas consecutivas.

- **Backend:** Django 6 + Django REST Framework + SQLite (API-first, multiusuario
  con el auth nativo de Django).
- **Frontend:** React 19 + Vite + Tailwind v4 + shadcn/ui (tema oscuro, acento
  esmeralda), interfaz en español e inglés (react-i18next).

## Desarrollo

Requisitos: [uv](https://docs.astral.sh/uv/), Node 20+ y gettext
(`brew install gettext`) para compilar las traducciones del backend.

```bash
./dev.sh
```

Eso sincroniza dependencias, migra la base, compila traducciones y levanta los
dos servidores:

- Frontend: http://localhost:5173/ (Vite, con proxy de `/api`, `/accounts` y
  `/admin` al backend)
- API: http://127.0.0.1:8000/api/

La app requiere login (`/accounts/login/`). El primer usuario sale de la
sección siguiente.

### Superusuario, admin y consola de Django

Todos los comandos se corren desde `backend/`.

```bash
cd backend

# Crear un superusuario nuevo (pide username, email y contraseña):
uv run python manage.py createsuperuser

# O, si el usuario ya existe (p. ej. "davidjaras", creado por la migración
# de datos), definirle/cambiarle la contraseña:
uv run python manage.py changepassword davidjaras

# Migraciones:
uv run python manage.py makemigrations   # generar tras cambiar modelos
uv run python manage.py migrate          # aplicar

# Servidor de desarrollo solo-backend (si no usás ./dev.sh):
uv run python manage.py runserver 8000

# Consola interactiva de Django:
uv run python manage.py shell
```

- **Admin:** http://127.0.0.1:8000/admin/ (o http://localhost:5173/admin/ con
  el proxy de Vite) — requiere un usuario con `is_staff`. Los modelos del
  tracker (Session, ActiveTimer, Measurement, WeeklyGoal) están registrados.
- **Login de la app:** http://localhost:5173/accounts/login/. Cambio de
  contraseña en `/accounts/password_change/`; reset en
  `/accounts/password_reset/` (en desarrollo el email se imprime en la
  consola del `runserver`).

### Tests

```bash
cd backend && uv run pytest
```

Cubren la lógica de negocio (agregación diaria/semanal, acumulado de la semana
en curso, meta cumplida, racha, cronómetro con pausas), el flujo de registro
vía API y la separación de datos entre usuarios.

### Estructura

```
backend/
  config/            # settings y URLs raíz
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
dev.sh               # levanta ambos servidores locales
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

## Deploy (una sola máquina)

Pensado para un VPS chico o un server casero (Linux con systemd). La misma
instancia de Django sirve la API y el frontend compilado (WhiteNoise), así que
hay **un solo servicio**. Los pasos están documentados y verificados en local;
no hay nada desplegado.

### 1. Preparar la máquina

```bash
# Como root o con sudo
apt update && apt install -y git curl
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt install -y nodejs
useradd -m -s /bin/bash ohara                             # usuario de servicio
su - ohara
git clone <URL-del-repo> ~/ohara
```

### 2. Compilar el frontend

```bash
cd ~/ohara/frontend
npm ci
npm run build        # genera frontend/dist, que Django sirve en producción
```

### 3. Configurar el backend

```bash
cd ~/ohara/backend
uv sync --no-dev

# Variables de entorno (guardalas en /home/ohara/ohara/.env.prod)
cat > ../.env.prod << 'EOF'
OHARA_DEBUG=0
OHARA_SECRET_KEY=<generar: python3 -c "import secrets; print(secrets.token_urlsafe(50))">
OHARA_ALLOWED_HOSTS=<tu-host-o-IP>
OHARA_TIME_ZONE=America/Bogota
EOF

set -a; source ../.env.prod; set +a
uv run python manage.py migrate
uv run python manage.py compilemessages -l es   # necesita gettext (apt install gettext)
uv run python manage.py collectstatic --no-input

# Contraseña de tu usuario (la migración lo crea sin contraseña utilizable):
uv run python manage.py changepassword davidjaras
```

Nota: el reset de contraseña por email requiere configurar SMTP (variables
`EMAIL_*` de Django) en producción; si no, usá `changepassword` por consola.

Verificación rápida (opcional): `uv run gunicorn config.wsgi -b 127.0.0.1:8000`
y abrir `http://<host>:8000/`.

### 4. Servicio systemd

`/etc/systemd/system/ohara.service`:

```ini
[Unit]
Description=ohara (Django + SPA)
After=network.target

[Service]
User=ohara
WorkingDirectory=/home/ohara/ohara/backend
EnvironmentFile=/home/ohara/ohara/.env.prod
ExecStart=/home/ohara/.local/bin/uv run gunicorn config.wsgi \
    --bind 127.0.0.1:8000 --workers 2
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ohara
```

### 5. Exponerla (elegir una)

- **Solo para vos (recomendado):** instalá [Tailscale](https://tailscale.com/)
  en el server y tus dispositivos; accedé por la IP privada de tailnet sin
  abrir puertos. Con esto podés dejar `--bind 0.0.0.0:8000` y
  `OHARA_ALLOWED_HOSTS=<ip-tailscale>`.
- **Con dominio público:** poné [Caddy](https://caddyserver.com/) delante
  (TLS automático): `caddy reverse-proxy --from ohara.tudominio.com --to 127.0.0.1:8000`.
  La app no tiene auth (un solo usuario), así que si es pública, protegela
  (p. ej. `basic_auth` de Caddy).

### 6. Backups

Todo el estado vive en `backend/db.sqlite3`. Un cron diario alcanza:

```bash
0 3 * * * sqlite3 /home/ohara/ohara/backend/db.sqlite3 ".backup /home/ohara/backups/ohara-$(date +\%F).sqlite3"
```

### Actualizar

```bash
cd ~/ohara && git pull
cd frontend && npm ci && npm run build
cd ../backend && uv sync --no-dev && set -a; source ../.env.prod; set +a
uv run python manage.py migrate && uv run python manage.py collectstatic --no-input
sudo systemctl restart ohara
```
