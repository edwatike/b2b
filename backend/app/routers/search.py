from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db import async_session
from app.models.company import Company
from app.services.parser import search_suppliers
from app.schemas.query import SearchRequest, SearchResponse
import logging

logger = logging.getLogger(__name__)

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
async def search(request: SearchRequest) -> SearchResponse:
    """
    Поиск поставщиков по запросу
    """
    try:
        logger.info(f"Получен запрос на поиск: {request.query}")
        results = await search_suppliers(request.query)
        logger.info(f"Найдено {len(results)} результатов")
        return SearchResponse(results=results)
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса поиска: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
