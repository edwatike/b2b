# Use official Python image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY ./pyproject.toml ./poetry.lock* /app/
RUN pip install --upgrade pip && pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Copy the rest of the app
COPY . /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command for production (gunicorn with uvicorn worker)
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
