from typing import List, Dict, Optional
from urllib.parse import urlparse
from sqlalchemy import select
from app.db.session import async_session
from app.models.search_result import SearchResult
from .playwright_runner import PlaywrightRunner
from .parser_config import ParserConfig
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

class ParserService:
    def __init__(self):
        self.config = ParserConfig()
        self.playwright_runner = PlaywrightRunner(config=self.config)
        
    async def search_and_save(self, keyword: str, max_results: int = 1000, search_engine: str = "yandex") -> List[Dict[str, str]]:
        """Выполняет поиск и сохраняет результаты в базу данных.
        
        Args:
            keyword: Ключевое слово для поиска
            max_results: Максимальное количество результатов
            search_engine: Поисковая система (yandex или google)
            
        Returns:
            List[Dict[str, str]]: Список результатов поиска
        """
        try:
            # Проверяем кэш
            cached_results = await self.get_cached_results(keyword, max_results)
            if cached_results:
                logger.info(f"Найдены кэшированные результаты для запроса '{keyword}'")
                return cached_results

            # Выполняем поиск
            if search_engine == "yandex":
                from .search_yandex import search_yandex
                results = await search_yandex(query=keyword, limit=max_results)
            else:
                from .search_google import search_google
                results = await search_google(query=keyword, limit=max_results)
            
            # Сохраняем результаты в базу данных
            if results:
                await self.save_results(keyword, results)
                logger.info(f"Сохранено {len(results)} результатов для запроса '{keyword}'")
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска: {str(e)}")
            raise
            
    async def get_cached_results(self, keyword: str, max_results: int) -> Optional[List[Dict[str, str]]]:
        """Проверяет наличие кэшированных результатов поиска.
        
        Args:
            keyword: Ключевое слово для поиска
            max_results: Максимальное количество результатов
            
        Returns:
            Optional[List[Dict[str, str]]]: Список кэшированных результатов или None
        """
        try:
            async with async_session() as session:
                # Получаем кэшированные результаты
                results = await session.execute(
                    select(SearchResult)
                    .where(SearchResult.query == keyword)
                    .limit(max_results)
                )
                cached_results = results.scalars().all()
                
                if cached_results:
                    return [{
                        "url": result.url,
                        "title": result.title or "",
                        "domain": result.domain or ""
                    } for result in cached_results]
                    
        except Exception as e:
            logger.error(f"Ошибка при получении кэшированных результатов: {str(e)}")
            
        return None
        
    async def save_results(self, keyword: str, results: List[Dict[str, str]]) -> None:
        """Сохраняет результаты поиска в базу данных.
        
        Args:
            keyword: Ключевое слово для поиска
            results: Список результатов поиска
        """
        try:
            async with async_session() as session:
                for result in results:
                    # Извлекаем домен из URL
                    parsed_url = urlparse(result["url"])
                    domain = parsed_url.netloc
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    
                    search_result = SearchResult(
                        url=result["url"],
                        result_url=result["url"],  # Используем тот же URL
                        title=result.get("title", ""),
                        domain=domain,
                        query=keyword
                    )
                    session.add(search_result)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов: {str(e)}")
            raise 