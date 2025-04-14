#!/bin/bash

# Проверяем, что аргумент передан
if [ -z "$1" ]; then
    echo "Использование: ./switch_search.sh [yandex|google|both]"
    exit 1
fi

# Проверяем корректность аргумента
if [ "$1" != "yandex" ] && [ "$1" != "google" ] && [ "$1" != "both" ]; then
    echo "Ошибка: допустимые значения - yandex, google или both"
    exit 1
fi

# Обновляем корневой .env файл
if grep -q "^SEARCH_MODE=" .env; then
    # Если строка существует, обновляем её
    sed -i "s/^SEARCH_MODE=.*/SEARCH_MODE=$1/" .env
else
    # Если строки нет, добавляем её
    echo "SEARCH_MODE=$1" >> .env
fi

# Обновляем .env файл в backend
if grep -q "^SEARCH_MODE=" backend/.env; then
    # Если строка существует, обновляем её
    sed -i "s/^SEARCH_MODE=.*/SEARCH_MODE=$1/" backend/.env
else
    # Если строки нет, добавляем её
    echo "SEARCH_MODE=$1" >> backend/.env
fi

# Перезапускаем контейнеры
docker-compose down
docker-compose up -d

echo "Режим поиска переключен на: $1"
echo "Для проверки текущего режима используйте: curl http://localhost:8001/api/parser/search/mode" 