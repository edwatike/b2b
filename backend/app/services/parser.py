import logging
from app.parser.search_scraperapi import search_scraperapi
from app.schemas.query import SearchResponse, ResultItem
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

async def search_suppliers(query: str) -> List[ResultItem]:
    """
    Поиск поставщиков по запросу
    """
    try:
        logger.info(f"Начинаем поиск поставщиков для запроса: {query}")
        
        # Получаем результаты через ScraperAPI
        raw_results = await search_scraperapi(query)
        logger.info(f"Получено {len(raw_results)} результатов от ScraperAPI")
        
        # Преобразуем результаты в нужный формат
        results = []
        for raw_result in raw_results:
            result = ResultItem(
                company=raw_result.get("title", ""),
                website=raw_result.get("link", ""),
                email="",  # Пока оставляем пустым, так как не извлекаем email
                product_found=True  # Предполагаем, что если результат найден, то продукт существует
            )
            results.append(result)
            
        # Логируем первые 3 результата для отладки
        for i, result in enumerate(results[:3], 1):
            logger.debug(f"Результат {i}: {result.dict()}")
        
        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске поставщиков: {str(e)}", exc_info=True)
        raise
