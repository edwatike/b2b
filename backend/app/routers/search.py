from fastapi import APIRouter, Query
from app.services.parser import search_suppliers
from app.schemas.query import SearchRequest, SearchResponse

router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search(query: SearchRequest):
    return await search_suppliers(query)
