import logging
from typing import List, Dict, Any, Optional
from .playwright_runner import PlaywrightRunner
from .config.parser_config import config
from playwright.async_api import Page
import random
import asyncio
from urllib.parse import quote_plus
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class GoogleSearch:
    def __init__(self, playwright_runner: Optional[PlaywrightRunner] = None):
        self.playwright_runner = playwright_runner or PlaywrightRunner(config)
        
    async def search(self, query: str, max_results: int = 30) -> List[Dict[str, Any]]:
        """
        Выполняет поиск в Google через Playwright
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            
        Returns:
            List[Dict[str, Any]]: Список результатов поиска
        """
        try:
            results = []
            page = await self.playwright_runner.get_page()
            
            # Формируем URL для поиска
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={max_results}"
            
            # Переходим на страницу поиска
            await page.goto(search_url, wait_until="networkidle")
            await asyncio.sleep(random.uniform(1, 3))  # Случайная задержка
            
            # Ждем загрузки результатов
            await page.wait_for_selector("div.g", timeout=10000)
            
            # Собираем результаты
            search_results = await page.query_selector_all("div.g")
            
            if not search_results:
                logger.warning(f"No results found on page 1")
                return results
                
            for result in search_results:
                if len(results) >= max_results:
                    break
                    
                try:
                    # Извлекаем заголовок и ссылку
                    title_element = await result.query_selector("h3")
                    link_element = await result.query_selector("a")
                    
                    if title_element and link_element:
                        title = await title_element.inner_text()
                        href = await link_element.get_attribute("href")
                        
                        if href and not href.startswith(("javascript:", "data:")):
                            results.append({
                                "title": title,
                                "url": href,
                                "source": "google"
                            })
                except Exception as e:
                    logger.error(f"Error extracting result: {e}")
                    continue
            
            # Проверяем, есть ли кнопка "Следующая"
            next_button = await page.query_selector("a#pnnext")
            if not next_button:
                return results[:max_results]
                
            await asyncio.sleep(random.uniform(2, 4))  # Задержка между страницами
            
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error in Google search: {str(e)}")
            return []
            
        finally:
            if page:
                await self.playwright_runner.release_page(page)

async def search_google(query: str, limit: int = 10, pages: int = 1) -> List[Dict[str, str]]:
    """Выполняет поиск в Google и возвращает результаты.
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов
        pages: Количество страниц для парсинга
        
    Returns:
        List[Dict[str, str]]: Список результатов поиска
    """
    results = []
    logger.info(f"Начинаем поиск в Google по запросу '{query}' на {pages} страницах")
    
    try:
        # Инициализируем Playwright
        async with async_playwright() as playwright:
            # Создаем браузер и страницу
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                for page_num in range(pages):
                    start_index = page_num * 10
                    # Формируем URL для поиска
                    search_url = f"https://www.google.com/search?q={quote_plus(query)}&start={start_index}"
                    logger.info(f"Страница {page_num + 1}/{pages}: {search_url}")
                    
                    # Переходим на страницу поиска
                    await page.goto(search_url, wait_until="networkidle")
                    await asyncio.sleep(random.uniform(1, 3))  # Случайная задержка
                    
                    # Ждем загрузки результатов
                    await page.wait_for_selector("div.g", timeout=10000)
                    
                    # Собираем результаты
                    search_results = await page.query_selector_all("div.g")
                    
                    if not search_results:
                        logger.warning(f"На странице {page_num + 1} не найдено результатов")
                        break
                        
                    for result in search_results:
                        if len(results) >= limit:
                            logger.info(f"Достигнут лимит результатов ({limit})")
                            return results[:limit]
                            
                        try:
                            # Извлекаем заголовок и ссылку
                            title_element = await result.query_selector("h3")
                            link_element = await result.query_selector("a")
                            
                            if title_element and link_element:
                                title = await title_element.inner_text()
                                href = await link_element.get_attribute("href")
                                
                                if href and not href.startswith(("javascript:", "data:")):
                                    results.append({
                                        "title": title,
                                        "url": href,
                                        "domain": href.split('/')[2] if '/' in href else ""
                                    })
                                    logger.info(f"Найден результат: {title} -> {href}")
                        except Exception as e:
                            logger.error(f"Ошибка при извлечении результата: {e}")
                            continue
                    
                    # Проверяем, есть ли кнопка "Следующая"
                    next_button = await page.query_selector("a#pnnext")
                    if not next_button:
                        logger.info("Кнопка 'Следующая' не найдена, завершаем поиск")
                        break
                        
                    # Добавляем задержку между страницами
                    await asyncio.sleep(random.uniform(2, 4))
            finally:
                # Закрываем браузер
                await context.close()
                await browser.close()
        
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
    
    logger.info(f"Поиск завершен. Найдено результатов: {len(results)}")
    return results[:limit] 