from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import router  # Общий router (companies, и т.п.)
from app.api import search      # Новый парсинг эндпоинт
from app.routers import router_parser  # Новый роутер для парсинга
from app.db import init_db
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="B2B Backend",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Разрешаем доступ извне
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Основные маршруты (из app/routers)
app.include_router(router, prefix="/api")

# Подключаем парсинговый search отдельно (из app/api/search.py)
app.include_router(search.router, prefix="/api")

# Подключаем новый роутер для парсинга
app.include_router(router_parser.router, prefix="/api")

# Инициализация БД при старте
@app.on_event("startup")
async def startup_event():
    await init_db()

# Простой тестовый маршрут
@app.get("/")
def root():
    return {"message": "B2B backend запущен 👋"}
