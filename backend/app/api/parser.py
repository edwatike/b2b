from fastapi import APIRouter, Depends, BackgroundTasks
from typing import Optional
import logging
from ..parser.models import SearchRequest, SearchResponse
from ..parser.parser_service import ParserService
from ..parser.search_google import GoogleSearch
from ..parser.playwright_runner import PlaywrightRunner
from ..parser.config.parser_config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parser", tags=["parser"])

# Global instances
playwright_runner = None
google_search = None

@router.on_event("startup")
async def startup_event():
    """Initialize parser service on startup."""
    global playwright_runner, google_search
    playwright_runner = PlaywrightRunner(config)
    await playwright_runner.initialize()
    google_search = GoogleSearch(playwright_runner)
    logger.info("✅ Parser service initialized")

@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    global playwright_runner
    if playwright_runner:
        await playwright_runner.cleanup()
    logger.info("✅ Parser service cleaned up")

@router.post("/search")
async def search(
    request: SearchRequest,
    background_tasks: BackgroundTasks
) -> SearchResponse:
    """
    Search for companies based on query, region, and category.
    Returns both cached and new results.
    """
    try:
        logger.info(f"Получен запрос на поиск: {request.query}")
        
        # Выполняем поиск через Google
        results = await google_search.search(
            query=request.query,
            region=request.region,
            limit=request.limit
        )
        
        # Формируем ответ
        response = SearchResponse(
            results=results,
            total=len(results),
            cached=0,
            new=len(results)
        )
        
        logger.info(f"Найдено результатов: {response.total}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing search request: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return SearchResponse(results=[], total=0, cached=0, new=0) 