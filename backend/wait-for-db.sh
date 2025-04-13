#!/bin/bash
set -e

host="$1"
shift

echo "Проверяем подключение к базе данных..."
echo "Host: $host"
echo "User: $POSTGRES_USER"
echo "Database: $POSTGRES_DB"

until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "⏳ Ждём Postgres ($host)..."
  sleep 2
done

echo "✅ Postgres готов, запускаем команду: $@"
exec "$@" 