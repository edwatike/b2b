from .search_scraperapi import search_scraperapi
import asyncio
from typing import List
import logging
from fastapi import APIRouter, BackgroundTasks
from .models import SearchRequest, SearchResponse
from .parser_service import ParserService
from .playwright_runner import PlaywrightRunner
from .search_google import GoogleSearch
from .config.parser_config import config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/test", tags=["test"])

# Глобальные объекты для теста
playwright_runner = None
google_search = None

@router.on_event("startup")
async def startup_event():
    """Инициализируем необходимые объекты"""
    global playwright_runner, google_search
    playwright_runner = PlaywrightRunner(config)
    await playwright_runner.initialize()
    google_search = GoogleSearch(playwright_runner)
    logger.info("✅ Test API initialized")

@router.on_event("shutdown") 
async def shutdown_event():
    """Освобождаем ресурсы"""
    global playwright_runner
    if playwright_runner:
        await playwright_runner.cleanup()
    logger.info("✅ Test API resources released")

@router.post("/search")
async def search_test(request: SearchRequest) -> SearchResponse:
    """
    Тестовый эндпоинт для поиска через Google
    """
    try:
        logger.info(f"Получен тестовый запрос на поиск: {request.query}")
        
        # Выполняем поиск через Google
        results = await google_search.search(
            query=request.query,
            max_results=request.limit
        )
        
        # Создаем ответ
        response = SearchResponse(
            results=results,
            total=len(results),
            cached=0,
            new=len(results)
        )
        
        logger.info(f"Найдено результатов: {len(results)}")
        return response
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении тестового поиска: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return SearchResponse(results=[], total=0, cached=0, new=0)

async def parse_all_sources(query: str) -> List[str]:
    """
    Парсинг из всех источников
    """
    # Запускаем поиск только через ScraperAPI
    search_tasks = [
        search_scraperapi(query)
    ]
    
    # Ждем результаты
    results = await asyncio.gather(*search_tasks, return_exceptions=True)
    
    # Объединяем результаты, исключая ошибки
    all_links = []
    for result in results:
        if isinstance(result, List) and result:
            all_links.extend(result)
    
    # Удаляем дубликаты, сохраняя порядок
    unique_links = list(dict.fromkeys(all_links))
    
    logger.info(f"Всего найдено уникальных результатов: {len(unique_links)}")
    return unique_links