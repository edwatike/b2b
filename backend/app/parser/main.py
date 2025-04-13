from .search_scraperapi import search_scraperapi
import asyncio
from typing import List
import logging

logger = logging.getLogger(__name__)

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