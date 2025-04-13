from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db import async_session
from app.models.company import Company
from app.services.parser import search_suppliers
from app.schemas.query import SearchRequest, SearchResponse

router = APIRouter()

# Получаем сессию БД
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

# Поиск компаний по названию
@router.get("/")
async def search(query: str, session: AsyncSession = Depends(get_session)):
    statement = select(Company).where(Company.name.contains(query))
    results = await session.execute(statement)
    return {
        "query": query,
        "results": results.scalars().all()
    }

@router.post("/search", response_model=SearchResponse)
async def search_post(query: SearchRequest):
    return await search_suppliers(query)
