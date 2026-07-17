#!/usr/bin/env bash
# Launch both local servers: Django API (:8000) and Vite frontend (:5173).
# Ctrl-C stops both. Requires uv (backend) and npm (frontend).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure backend deps + venv exist and the DB is migrated.
(cd "$ROOT/backend" && uv sync -q && uv run python manage.py migrate --no-input)

# Ensure frontend deps exist.
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm install)
fi

cleanup() {
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd "$ROOT/backend" && uv run python manage.py runserver 8000) &
(cd "$ROOT/frontend" && npm run dev) &

echo
echo "  API:      http://127.0.0.1:8000/api/"
echo "  Frontend: http://localhost:5173/"
echo

wait
