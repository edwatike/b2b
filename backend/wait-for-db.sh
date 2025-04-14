#!/bin/bash
set -e

host="$1"
shift

echo "Проверяем подключение к базе данных..."
echo "Host: $host"
echo "User: $POSTGRES_USER"
echo "Database: $POSTGRES_DB"
echo "Password: $POSTGRES_PASSWORD"
echo "DATABASE_URL: $DATABASE_URL"

until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "⏳ Ждём Postgres ($host)..."
  sleep 1
done

>&2 echo "✅ Postgres готов"

echo "✅ Postgres готов, запускаем команду: $@"
exec "$@" 