# ohara

App personal para trackear tiempo de estudio, inspirada en el modelo de metas
semanales de Garmin: meta semanal en minutos, gráficas por día y por semana,
chulito verde en las semanas cumplidas y racha de semanas consecutivas.

- **Backend:** Django 6 + Django REST Framework + SQLite (API-first, un solo usuario).
- **Frontend:** React 19 + Vite + Tailwind v4 + shadcn/ui (tema oscuro, acento esmeralda).

## Desarrollo

Requisitos: [uv](https://docs.astral.sh/uv/) y Node 20+.

```bash
./dev.sh
```

Eso sincroniza dependencias, migra la base y levanta los dos servidores:

- Frontend: http://localhost:5173/ (Vite, con proxy de `/api` al backend)
- API: http://127.0.0.1:8000/api/

### Tests

```bash
cd backend && uv run pytest
```

Cubren la lógica de negocio (agregación diaria/semanal, meta cumplida, racha,
cronómetro con pausas) y el flujo de registro vía API.

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
| GET | `/api/stats/?metric=&days=&weeks=` | Payload del dashboard |

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
uv run python manage.py collectstatic --no-input
```

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
