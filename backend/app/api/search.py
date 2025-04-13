from fastapi import APIRouter
from app.parser.main import parse_all_sources

router = APIRouter()

@router.get("/search")
async def search(query: str):
    results = await parse_all_sources(query)
    return {"query": query, "results": [r.dict() for r in results]}