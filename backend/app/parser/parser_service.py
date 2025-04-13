from app.parser.search_google import search_google
import logging
import asyncio
from typing import List, Dict, Any
from .scraperapi_client import scrape_url_with_scraperapi
from urllib.parse import quote
from app.models.search_result import SearchResult
from app.db import async_session
from .search_scraperapi import search_scraperapi
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import select

logger = logging.getLogger(__name__)

async def run_full_parse(keyword: str, max_results: int = 20):
    """
    Выполняет полный парсинг и сохраняет результаты в базу данных
    """
    results = await search_google(keyword, max_results)
    
    async with async_session() as session:
        for item in results:
            db_item = SearchResult(
                query=keyword,
                result_url=item['link'],
                title=item.get('title'),
                snippet=item.get('snippet')
            )
            session.add(db_item)
        await session.commit()
        
    return results

async def run_scraperapi_parse(keyword: str, geo: str) -> str:
    """
    Парсит результаты поиска через ScraperAPI.
    
    Args:
        keyword: Ключевое слово для поиска
        geo: Географический регион для поиска
        
    Returns:
        str: HTML-код страницы с результатами поиска
    """
    # Формируем поисковый URL
    search_query = f"{keyword} {geo}"
    encoded_query = quote(search_query)
    search_url = f"https://www.google.com/search?q={encoded_query}&hl=ru"
    
    logger.info(f"Начинаем парсинг через ScraperAPI для запроса: {search_query}")
    logger.info(f"URL для парсинга: {search_url}")
    
    html = await scrape_url_with_scraperapi(search_url)
    
    if html:
        logger.info("Успешно получен HTML через ScraperAPI")
        return html
    else:
        logger.error("Не удалось получить HTML через ScraperAPI")
        return ""

async def test_scraperapi():
    """
    Тестовая функция для демонстрации работы ScraperAPI.
    Парсит тестовую страницу и выводит результат в консоль.
    """
    test_url = "https://httpbin.org/html"
    logger.info(f"Начинаем тестовый парсинг URL: {test_url}")
    
    html = await scrape_url_with_scraperapi(test_url)
    
    if html:
        logger.info("Успешно получен HTML:")
        logger.info(html[:500] + "...")  # Выводим первые 500 символов
    else:
        logger.error("Не удалось получить HTML")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=10),
    reraise=True
)
async def search_and_save(keyword: str, max_results: int = 1000) -> List[Dict[str, Any]]:
    """
    Выполняет поиск через ScraperAPI и сохраняет результаты в базу данных
    
    Args:
        keyword: Ключевое слово для поиска
        max_results: Максимальное количество результатов (по умолчанию 1000)
        
    Returns:
        List[Dict[str, Any]]: Список результатов поиска
        
    Raises:
        Exception: В случае ошибки при поиске или сохранении результатов
    """
    try:
        logger.info(f"Начинаем поиск по запросу: {keyword}")
        results = await search_scraperapi(keyword, max_results)
        logger.info(f"Найдено результатов: {len(results)}")
        
        async with async_session() as session:
            # Получаем существующие URL из базы для этого запроса
            stmt = select(SearchResult.result_url).where(SearchResult.query == keyword)
            existing_urls = {r[0] for r in (await session.execute(stmt)).all()}
            
            # Фильтруем дубликаты
            new_results = [
                SearchResult(
                    query=keyword,
                    result_url=item['link'],
                    title=item.get('title'),
                    snippet=item.get('snippet')
                )
                for item in results
                if item['link'] not in existing_urls
            ]
            
            if new_results:
                try:
                    # Добавляем все объекты одним запросом
                    session.add_all(new_results)
                    await session.commit()
                    logger.info(f"Сохранено {len(new_results)} новых результатов в базу данных")
                except SQLAlchemyError as e:
                    await session.rollback()
                    logger.error(f"Ошибка при сохранении в базу данных: {str(e)}")
                    raise
            else:
                logger.info("Новых результатов не найдено")
                
        return results
    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=1, max=10),
    reraise=True
)
async def scrape_url(url: str) -> str:
    """
    Парсит указанный URL через ScraperAPI с механизмом retry
    
    Args:
        url: URL для парсинга
        
    Returns:
        str: HTML-код страницы
    """
    logger.info(f"Начинаем парсинг URL: {url}")
    html = await scrape_url_with_scraperapi(url)
    if not html:
        logger.error(f"Не удалось получить HTML для {url}")
        return ""
    logger.info(f"Успешно получен HTML для {url}")
    return html

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_scraperapi())
