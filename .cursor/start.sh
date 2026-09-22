#!/usr/bin/env bash
# Per-boot service startup for the ROR API Cloud Agent environment.
# Starts MySQL and Elasticsearch, applies migrations and ensures the
# v2 Elasticsearch index exists. Idempotent and safe to re-run.
set -euo pipefail

cd "$(dirname "$0")/.."

# Ensure local dev config exists even if the checkout dropped it.
if [ ! -f .env ]; then
  cp .cursor/env.example .env
fi

echo "start.sh: starting MySQL..."
# Initialize the data directory if the image did not already do so.
# (/var/lib/mysql is mode 700 mysql:mysql, so probe it with sudo. MySQL 8
# stores the system schema in mysql.ibd rather than a mysql/ directory.)
if ! sudo test -f /var/lib/mysql/mysql.ibd; then
  sudo mkdir -p /var/lib/mysql
  sudo chown -R mysql:mysql /var/lib/mysql
  sudo mysqld --initialize-insecure --user=mysql
fi
sudo mkdir -p /var/run/mysqld
sudo chown mysql:mysql /var/run/mysqld
sudo service mysql start || true
for i in $(seq 1 60); do
  if sudo mysqladmin ping >/dev/null 2>&1; then break; fi
  sleep 1
done
sudo mysql < .cursor/mysql-init.sql
echo "start.sh: MySQL ready"

echo "start.sh: starting Elasticsearch..."
if ! curl -s -m 3 http://127.0.0.1:9200 >/dev/null 2>&1; then
  # Detach all standard fds so the daemon does not hold this command's
  # stdout/stderr pipe open (otherwise `start` never returns and boot stalls).
  sudo -u elasticsearch ES_PATH_CONF=/opt/elasticsearch/config \
    /opt/elasticsearch/bin/elasticsearch -d -p /tmp/es.pid \
    </dev/null >/tmp/elasticsearch-console.log 2>&1
fi
for i in $(seq 1 90); do
  if curl -s -m 3 http://127.0.0.1:9200 >/dev/null 2>&1; then break; fi
  sleep 2
done
echo "start.sh: Elasticsearch ready"

# Database migrations (idempotent) and v2 index creation.
./.venv/bin/python manage.py migrate --noinput
if [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9200/organizations-v2)" != "200" ]; then
  ./.venv/bin/python manage.py createindex || true
fi

echo "start.sh: ROR API services ready"
