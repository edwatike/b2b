from celery import Celery
from app.core.config import settings

celery = Celery(
    "worker",
    broker=settings.REDIS_BROKER,
    backend=settings.REDIS_BROKER
)

@celery.task
def dummy_task():
    return "I'm alive!"
