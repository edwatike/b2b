from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import search

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов
app.include_router(search.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "B2B backend запущен 👋"}
