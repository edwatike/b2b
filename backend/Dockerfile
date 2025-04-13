FROM python:3.12-slim-bullseye

# Настраиваем сеть
ENV DEBIAN_FRONTEND=noninteractive
RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99pipelines && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99pipelines && \
    echo "Acquire::http::Keep-Alive false;" >> /etc/apt/apt.conf.d/99pipelines

WORKDIR /app

# Копируем конфиг pip
COPY pip.conf /etc/pip.conf

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Команда запуска
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
