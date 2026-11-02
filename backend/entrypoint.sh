#!/bin/sh
set -e

if [ -n "${POSTGRES_DB}" ]; then
    echo "Waiting for database at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432} ..."
    ATTEMPTS=0
    until python -c "import django; django.setup(); from django.db import connection; connection.ensure_connection()" 2>/dev/null; do
        ATTEMPTS=$((${ATTEMPTS} + 1))
        if [ "${ATTEMPTS}" -ge 30 ]; then
            echo "Database not reachable after ${ATTEMPTS} attempts, giving up."
            exit 1
        fi
        sleep 1
    done
    echo "Database is reachable."
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
