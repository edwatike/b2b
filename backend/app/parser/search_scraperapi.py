import httpx
from bs4 import BeautifulSoup
import logging
from typing import List
import os
from urllib.parse import quote
import asyncio

logger = logging.getLogger(__name__)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
MAX_PAGES = 10  # Максимальное количество страниц
RESULTS_PER_PAGE = 100  # Результатов на странице

async def fetch_page(client: httpx.AsyncClient, url: str) -> List[str]:
    """
    Получение результатов с одной страницы
    """
    try:
        response = await client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        # Ищем все ссылки в результатах поиска
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if href.startswith('http') and not href.startswith('http://api.scraperapi.com'):
                if not any(skip in href.lower() for skip in [
                    'google.com', 
                    'accounts.google', 
                    'support.google', 
                    'translate.google',
                    'webcache.google',
                    'policies.google'
                ]):
                    links.append(href)
        return links
    except Exception as e:
        logger.error(f"Ошибка при получении страницы: {str(e)}")
        return []

async def search_scraperapi(query: str, max_results: int = 1000) -> List[str]:
    """
    Поиск через ScraperAPI
    """
    if not SCRAPER_API_KEY:
        logger.error("SCRAPER_API_KEY не установлен")
        return []

    try:
        all_links = []
        encoded_query = quote(query)
        
        # Создаем список URL для всех страниц
        urls = []
        for start in range(0, MAX_PAGES * RESULTS_PER_PAGE, RESULTS_PER_PAGE):
            url = f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}&url=https://www.google.com/search?q={encoded_query}&num={RESULTS_PER_PAGE}&start={start}"
            urls.append(url)

        logger.info(f"Отправляем {len(urls)} запросов к ScraperAPI для поиска: {query}")
        
        # Асинхронно получаем результаты со всех страниц
        async with httpx.AsyncClient(timeout=60) as client:
            tasks = [fetch_page(client, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for page_links in results:
                if isinstance(page_links, list):
                    all_links.extend(page_links)

        # Удаляем дубликаты и сортируем
        unique_links = sorted(list(dict.fromkeys(all_links)))
        logger.info(f"Найдено уникальных результатов через ScraperAPI: {len(unique_links)}")
        
        # Возвращаем все найденные результаты, но не более max_results
        return unique_links[:max_results]

    except Exception as e:
        logger.error(f"Ошибка при поиске через ScraperAPI: {str(e)}")
        return [] 