import logging
import asyncio
from typing import List, Dict, Any, Set, Optional
from app.models.search_result import SearchResult
from app.db import async_session
from sqlalchemy.exc import SQLAlchemyError
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime
from sqlmodel import select
from bs4 import BeautifulSoup
import traceback
import sys
import json

from .models import SearchRequest, SearchResponse
from .playwright_runner import PlaywrightRunner
from .search_google import GoogleSearch
from .config.parser_config import config
from .utils import (
    extract_domain,
    extract_emails,
    extract_phones,
    clean_text,
    clean_url
)
from ..database import async_session

logger = logging.getLogger(__name__)

# Устанавливаем максимально подробный уровень логирования
logging.basicConfig(level=logging.DEBUG)

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
    logger.info(f"🔍 НАЧИНАЕМ ПОИСК ПО ЗАПРОСУ: {keyword}")
    print(f"🔍 НАЧИНАЕМ ПОИСК ПО ЗАПРОСУ: {keyword}")
    
    try:
        # Инициализация Playwright
        playwright_runner = PlaywrightRunner()
        try:
            logger.info("Инициализация Playwright...")
            await playwright_runner.initialize()
            logger.info("✅ Playwright успешно инициализирован")
            
            # Создание экземпляра SearchEngine с инициализированным Playwright
            search_engine = SearchEngine(playwright_runner)
            logger.info("Запуск поиска в Google...")
            
            # Выполнение поиска и получение списка URL-адресов
            try:
                # Временный тестовый код для отладки - прямой запуск Playwright
                logger.info("🧪 ТЕСТОВЫЙ ЗАПУСК: прямое использование Playwright для поиска")
                
                # Получаем страницу из пула
                page = await playwright_runner.get_page()
                logger.info("✅ Страница получена из пула")
                
                try:
                    # Упрощенная версия для отладки - открываем Google напрямую
                    logger.info("Переходим на Google...")
                    content = await playwright_runner.navigate(page, "https://www.google.ru")
                    
                    if content:
                        logger.info("✅ Успешно загружена страница Google")
                        logger.debug(f"Первые 500 символов контента: {content[:500]}")
                    else:
                        logger.error("❌ Не удалось загрузить страницу Google")
                        
                    # Вводим поисковый запрос
                    logger.info(f"Вводим поисковый запрос: {keyword}")
                    await playwright_runner.type_search_query(page, keyword, "textarea[name='q']")
                    logger.info("✅ Поисковый запрос введен")
                    
                    # Ждем загрузки результатов
                    logger.info("Ожидаем загрузки результатов...")
                    await page.wait_for_load_state("networkidle", timeout=60000)
                    logger.info("✅ Страница результатов загружена")
                    
                    # Получаем контент страницы с результатами
                    content = await page.content()
                    if content:
                        logger.info(f"✅ Получен контент страницы (размер: {len(content)} байт)")
                        
                        # Сохраняем HTML для отладки
                        with open("/tmp/google_results.html", "w", encoding="utf-8") as f:
                            f.write(content)
                        logger.info("✅ HTML сохранен в /tmp/google_results.html")
                        
                        # Пытаемся извлечь результаты
                        soup = BeautifulSoup(content, 'html.parser')
                        logger.info("Ищем результаты на странице...")
                        
                        # Тестируем разные селекторы для поиска результатов
                        test_selectors = [
                            'div.yuRUbf > a',
                            '.kCrYT > a',
                            'a.l',
                            'div.g div.r a',
                            'div.tF2Cxc a',
                            'div.g div.yuRUbf a',
                            'a.cz3goc',
                            '.DhN8Cf a',
                            '.LC20lb',
                            'h3'  # Заголовки результатов
                        ]
                        
                        all_results = []
                        for selector in test_selectors:
                            results = soup.select(selector)
                            logger.info(f"Селектор '{selector}': найдено {len(results)} элементов")
                            
                            if results:
                                for i, result in enumerate(results[:5]):  # Выводим только первые 5 для отладки
                                    href = result.get('href') if hasattr(result, 'get') else None
                                    text = result.text if hasattr(result, 'text') else str(result)
                                    logger.info(f"  📌 Результат #{i+1}: href={href}, text={text[:100]}")
                                    
                                    if href and href.startswith('http'):
                                        all_results.append({
                                            "url": href,
                                            "title": text.strip() if text else "",
                                            "snippet": "",
                                            "position": i+1
                                        })
                        
                        logger.info(f"✅ Всего найдено уникальных результатов: {len(all_results)}")
                        
                        # Делаем скриншот для отладки
                        screenshot_path = "/tmp/google_results.png"
                        await page.screenshot(path=screenshot_path, full_page=True)
                        logger.info(f"✅ Скриншот сохранен в {screenshot_path}")
                        
                        return all_results[:max_results]
                    else:
                        logger.error("❌ Не удалось получить контент страницы результатов")
                        return []
                
                except Exception as e:
                    error_msg = f"❌ Ошибка при взаимодействии с Google: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return []
                
                finally:
                    # Возвращаем страницу обратно в пул
                    logger.info("Возвращаем страницу в пул...")
                    await playwright_runner.release_page(page)
                    logger.info("✅ Страница возвращена в пул")
                    
            except Exception as e:
                error_msg = f"❌ Ошибка при поиске: {str(e)}"
                logger.error(error_msg)
                logger.error(f"Traceback: {traceback.format_exc()}")
                return []
        
        finally:
            # Освобождаем ресурсы Playwright
            logger.info("Освобождаем ресурсы Playwright...")
            await playwright_runner.cleanup()
            logger.info("✅ Ресурсы Playwright освобождены")
    
    except Exception as e:
        error_msg = f"❌ Критическая ошибка: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

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

class ParserService:
    def __init__(self):
        self.playwright_runner = None
        self.google_search = None
        
    async def initialize(self):
        """Инициализирует все необходимые ресурсы"""
        self.playwright_runner = PlaywrightRunner()
        await self.playwright_runner.initialize()
        self.google_search = GoogleSearch(self.playwright_runner)
        logger.info("✅ Parser service инициализирован")
        
    async def cleanup(self):
        """Освобождает все ресурсы"""
        if self.playwright_runner:
            await self.playwright_runner.cleanup()
        logger.info("✅ Parser service освобожден")
    
    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Выполняет поиск по заданному запросу
        
        Args:
            request: Объект запроса поиска
            
        Returns:
            Объект ответа с результатами поиска
        """
        logger.info(f"Начинаем поиск по запросу: {request.query}")
        
        total_results = 0
        cached_count = 0
        new_count = 0
        all_results = []
        
        try:
            # Инициализируем ответ
            response = SearchResponse(results=[], total=0, cached=0, new=0)
            
            # Выполняем поиск через Google
            logger.info(f"Запускаем поиск в Google по запросу: '{request.query}'")
            search_results = await self.google_search.search(
                query=request.query,
                region=request.region,
                limit=request.limit
            )
            
            if search_results:
                logger.info(f"Найдено {len(search_results)} результатов в Google")
                
                # Преобразуем результаты в формат SearchResult для веб-API
                web_results = []
                for result in search_results:
                    web_result = SearchResult(
                        url=result.url,
                        title=result.title,
                        snippet=result.snippet,
                        position=result.position,
                        source="google"
                    )
                    web_results.append(web_result)
                
                # Обновляем ответ
                response.results = web_results
                response.total = len(web_results)
                response.new = len(web_results)
                
                logger.info(f"✅ Поиск выполнен успешно: найдено {response.total} результатов")
            else:
                logger.warning("⚠️ Не удалось найти результаты в Google")
                
            return response
                
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении поиска: {str(e)}")
            logger.error(traceback.format_exc())
            return SearchResponse(results=[], total=0, cached=0, new=0)
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_scraperapi())
