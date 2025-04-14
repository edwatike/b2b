from fastapi import APIRouter, HTTPException
from typing import List, Dict
import logging
from ..parser.models import SearchRequest, SearchResponse, SearchResult
from ..parser.parser_service import ParserService
from ..parser.playwright_runner import PlaywrightRunner
from ..parser.config.parser_config import config
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parser", tags=["parser"])

# Global instances
playwright_runner = None
parser_service = ParserService()

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    cached: int
    new: int

@router.on_event("startup")
async def startup_event():
    """Initialize parser service on startup."""
    global playwright_runner
    playwright_runner = PlaywrightRunner(config)
    await playwright_runner.initialize()
    logger.info("✅ Parser service initialized")

@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    global playwright_runner
    if playwright_runner:
        await playwright_runner.cleanup()
    logger.info("✅ Parser service cleaned up")

@router.post("/search")
async def search(request: SearchRequest) -> Dict:
    """
    Выполняет поиск по заданному запросу.
    
    Args:
        request: Параметры поискового запроса
        
    Returns:
        Dict: Результаты поиска
    """
    try:
        logger.info(f"Получен запрос на поиск: {request.query}")
        logger.info(f"Максимальное количество результатов: {request.limit}")
        
        results = await parser_service.search_and_save(request.query, request.limit)
        logger.info(f"Поиск завершен, найдено результатов: {len(results) if results else 0}")
        
        response = {
            "results": results,
            "total": len(results) if results else 0,
            "cached": 0,  # TODO: Добавить подсчет кэшированных результатов
            "new": len(results) if results else 0
        }
        logger.info(f"Отправляем ответ: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при выполнении поиска: {str(e)}") 