from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import logging
from ..parser.models import SearchRequest, SearchResponse, SearchResult
from ..parser.parser_service import ParserService
from ..parser.playwright_runner import PlaywrightRunner
from ..parser.config.parser_config import config
from pydantic import BaseModel
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parser", tags=["parser"])

# Global instances
playwright_runner = None
parser_service = ParserService()

class SearchRequest(BaseModel):
    query: str
    limit: int = 15

class SearchResponse(BaseModel):
    results: List[Dict[str, str]]
    total: int
    cached: int
    new: int
    search_mode: str

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

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Выполняет поиск по запросу.
    
    Args:
        request: Запрос на поиск, содержащий:
            - query: Поисковый запрос
            - limit: Максимальное количество результатов
            
    Returns:
        SearchResponse: Результаты поиска
    """
    try:
        logger.info(f"Получен запрос на поиск: {request.query}")
        logger.info(f"Максимальное количество результатов: {request.limit}")

        current_mode = parser_service.get_current_search_mode()
        logger.info(f"Текущий режим поиска: {current_mode}")

        results = await parser_service.search_and_save(
            keyword=request.query,
            max_results=request.limit
        )
        logger.info(f"Получены результаты: {results}")

        # Проверяем структуру результатов
        if not isinstance(results, dict):
            logger.error(f"Неверный тип результатов: {type(results)}")
            raise ValueError("Результаты должны быть словарем")

        if "results" not in results:
            logger.error(f"В результатах отсутствует ключ 'results': {results}")
            raise ValueError("В результатах отсутствует ключ 'results'")

        if not isinstance(results["results"], list):
            logger.error(f"results['results'] не является списком: {type(results['results'])}")
            raise ValueError("results['results'] должен быть списком")

        logger.info(f"Поиск завершен, найдено результатов: {len(results['results'])}")
        logger.info(f"Отправляем ответ: {results}")
        return results

    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}")
        logger.exception("Полный стек ошибки:")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/mode", response_model=dict)
async def get_search_mode():
    """Возвращает текущий режим поиска."""
    current_mode = parser_service.get_current_search_mode()
    return {"mode": current_mode} 