from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import router
from app.db import init_db  # 👈 добавь это

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.on_event("startup")
async def on_startup():
    await init_db()  # 👈 Вызов инициализации базы при старте

@app.get("/")
def root():
    return {"message": "B2B backend запущен 👋"}

