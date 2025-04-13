from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import router  # ✅ общий router, см. init
from app.db import init_db

app = FastAPI(
    title="B2B Backend",
    docs_url="/docs",            # ✅ Swagger по умолчанию
    redoc_url="/redoc",          # ✅ можно отключить, если не нужно
    openapi_url="/openapi.json"  # ✅ JSON описание API
)

# CORS — по-простому пока:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем маршруты
app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/")
def root():
    return {"message": "B2B backend запущен 👋"}

