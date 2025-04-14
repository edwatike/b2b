from fastapi import APIRouter
from app.parser.parser_service import search_and_save
from typing import Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 1000

router = APIRouter()

@router.get("/test")
async def test():
    """
    Тестовый маршрут для проверки работы роутера
    """
    logger.info("Тестовый маршрут вызван")
    return {"status": "ok"}

@router.post("/")
async def search(request: SearchRequest):
    """
    Выполняет поиск по запросу и сохраняет результаты в базу данных
    
    Args:
        request: Объект с параметрами поиска
        
    Returns:
        dict: Результаты поиска
    """
    logger.info(f"Получен запрос на поиск: {request.query}")
    try:
        results = await search_and_save(request.query, request.max_results)
        logger.info(f"Поиск завершен, найдено результатов: {len(results)}")
        return {"query": request.query, "results": results}
    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}")
        raise