FROM python:3.12-slim

# Настраиваем сеть и устанавливаем все необходимые пакеты в одном слое
ENV DEBIAN_FRONTEND=noninteractive
RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99pipelines && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99pipelines && \
    echo "Acquire::http::Keep-Alive false;" >> /etc/apt/apt.conf.d/99pipelines && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev \
    postgresql-client \
    wget \
    gnupg \
    unzip \
    # Добавляем и устанавливаем Chrome в том же слое
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    # Очищаем кэш и ненужные файлы
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

WORKDIR /app

# Копируем только необходимые файлы для установки зависимостей
COPY pip.conf /etc/pip.conf
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем скрипт ожидания и делаем его исполняемым
COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

# Копируем остальные файлы проекта
COPY . .

# Запускаем приложение
CMD ["/wait-for-db.sh", "db", "gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
