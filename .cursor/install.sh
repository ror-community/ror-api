#!/usr/bin/env bash
# Repository bootstrap for the ROR API Cloud Agent environment.
# Idempotent: safe to run repeatedly. Prepares the Python virtualenv,
# installs dependencies and collects static files. Runtime services
# (MySQL, Elasticsearch) are handled by start.sh.
set -euo pipefail

cd "$(dirname "$0")/.."

# Local dev configuration (settings.py loads this via python-dotenv).
if [ ! -f .env ]; then
  cp .cursor/env.example .env
fi

# Python virtualenv
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

# Static assets can be built without a database connection.
DJANGO_SKIP_DB_CHECK=True ./.venv/bin/python manage.py collectstatic --noinput

echo "install.sh: dependencies installed"
