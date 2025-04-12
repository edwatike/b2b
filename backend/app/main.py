from fastapi import FastAPI
from app.routers import search
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="B2B Supplier Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api", tags=["search"])

@app.get("/")
def read_root():
    return {"message": "Welcome to B2B API"}
