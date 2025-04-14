import logging
import traceback
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class Parser:
    def __init__(self):
        """Initialize parser with custom headers"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = None
        logger.debug("Parser initialized with custom headers")
        
    async def get_page_content(self, url: str) -> str:
        """Get page content using aiohttp"""
        logger.debug(f"\n=== Получение контента страницы ===")
        logger.debug(f"URL: {url}")
        
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
            logger.debug("Создана новая сессия aiohttp")
            
        try:
            async with self.session.get(url) as response:
                logger.debug(f"Статус ответа: {response.status}")
                if response.status == 200:
                    content = await response.text()
                    logger.debug(f"Получен контент, размер: {len(content)} байт")
                    logger.debug(f"Первые 100 символов: {content[:100]}")
                    return content
                else:
                    logger.error(f"Ошибка при получении страницы: {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"Ошибка при получении контента: {e}")
            logger.error(traceback.format_exc())
            return ""
            
    async def parse_yandex(self, query: str, limit: int = 30, pages: int = 3) -> List[Dict]:
        """Parse Yandex search results"""
        logger.debug(f"\n=== Парсинг результатов Яндекса ===")
        logger.debug(f"Запрос: {query}")
        logger.debug(f"Лимит: {limit}")
        logger.debug(f"Страниц: {pages}")
        
        results = []
        base_url = "https://yandex.ru/search/"
        
        try:
            for page in range(pages):
                logger.debug(f"\nОбработка страницы {page + 1}/{pages}")
                
                params = {
                    "text": query,
                    "p": page
                }
                
                url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
                logger.debug(f"URL запроса: {url}")
                
                content = await self.get_page_content(url)
                if not content:
                    logger.error(f"Не удалось получить контент для страницы {page + 1}")
                    continue
                    
                soup = BeautifulSoup(content, 'html.parser')
                search_results = soup.select("div.serp-item")
                
                logger.debug(f"Найдено результатов на странице: {len(search_results)}")
                
                for item in search_results:
                    try:
                        link = item.select_one("a.link")
                        if not link:
                            continue
                            
                        url = link.get("href", "")
                        title = link.get_text(strip=True)
                        
                        if url and title:
                            result = {
                                "url": url,
                                "title": title,
                                "html_content": None  # Будет заполнено позже
                            }
                            results.append(result)
                            logger.debug(f"Добавлен результат: {url}")
                            
                            if len(results) >= limit:
                                logger.info(f"Достигнут лимит результатов: {limit}")
                                return results
                                
                    except Exception as e:
                        logger.error(f"Ошибка при обработке результата: {e}")
                        logger.error(traceback.format_exc())
                        continue
                        
                # Задержка между запросами
                await asyncio.sleep(1)
                
            logger.info(f"Всего найдено результатов: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге Яндекса: {e}")
            logger.error(traceback.format_exc())
            return results
            
    async def parse_google(self, query: str, limit: int = 30, pages: int = 3) -> List[Dict]:
        """Parse Google search results"""
        logger.debug(f"\n=== Парсинг результатов Google ===")
        logger.debug(f"Запрос: {query}")
        logger.debug(f"Лимит: {limit}")
        logger.debug(f"Страниц: {pages}")
        
        results = []
        base_url = "https://www.google.com/search"
        
        try:
            for page in range(pages):
                logger.debug(f"\nОбработка страницы {page + 1}/{pages}")
                
                params = {
                    "q": query,
                    "start": page * 10
                }
                
                url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
                logger.debug(f"URL запроса: {url}")
                
                content = await self.get_page_content(url)
                if not content:
                    logger.error(f"Не удалось получить контент для страницы {page + 1}")
                    continue
                    
                soup = BeautifulSoup(content, 'html.parser')
                search_results = soup.select("div.g")
                
                logger.debug(f"Найдено результатов на странице: {len(search_results)}")
                
                for item in search_results:
                    try:
                        link = item.select_one("a")
                        title = item.select_one("h3")
                        
                        if not (link and title):
                            continue
                            
                        url = link.get("href", "")
                        title_text = title.get_text(strip=True)
                        
                        if url and title_text:
                            result = {
                                "url": url,
                                "title": title_text,
                                "html_content": None  # Будет заполнено позже
                            }
                            results.append(result)
                            logger.debug(f"Добавлен результат: {url}")
                            
                            if len(results) >= limit:
                                logger.info(f"Достигнут лимит результатов: {limit}")
                                return results
                                
                    except Exception as e:
                        logger.error(f"Ошибка при обработке результата: {e}")
                        logger.error(traceback.format_exc())
                        continue
                        
                # Задержка между запросами
                await asyncio.sleep(1)
                
            logger.info(f"Всего найдено результатов: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге Google: {e}")
            logger.error(traceback.format_exc())
            return results
            
    async def search(self, query: str, limit: int = 30, pages: int = 3, engine: str = "yandex") -> List[Dict]:
        """Perform search using specified engine"""
        logger.debug(f"\n=== Начало поиска ===")
        logger.debug(f"Запрос: {query}")
        logger.debug(f"Лимит: {limit}")
        logger.debug(f"Страниц: {pages}")
        logger.debug(f"Поисковая система: {engine}")
        
        try:
            if engine == "yandex":
                results = await self.parse_yandex(query, limit, pages)
            elif engine == "google":
                results = await self.parse_google(query, limit, pages)
            else:
                logger.error(f"Неподдерживаемая поисковая система: {engine}")
                return []
                
            logger.info(f"Поиск завершен, найдено результатов: {len(results)}")
            
            # Получаем HTML-контент для каждого результата
            logger.debug("\n=== Получение HTML-контента для результатов ===")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context()
                page = await context.new_page()
                
                for i, result in enumerate(results, 1):
                    try:
                        url = result.get('url')
                        if not url:
                            logger.error(f"Пропуск результата {i}: отсутствует URL")
                            continue
                            
                        logger.debug(f"\n--- Обработка результата {i}/{len(results)} ---")
                        logger.debug(f"URL: {url}")
                        
                        try:
                            # Загрузка страницы
                            logger.debug(f"Загрузка страницы...")
                            await page.goto(url, wait_until="networkidle", timeout=30000)
                            
                            # Получение HTML
                            html = await page.content()
                            
                            if html:
                                logger.debug(f"HTML получен успешно")
                                logger.debug(f"Размер HTML: {len(html)} байт")
                                logger.debug(f"Первые 100 символов: {html[:100]}")
                                result['html_content'] = html
                            else:
                                logger.error(f"Получен пустой HTML")
                                
                        except Exception as e:
                            logger.error(f"Ошибка при получении HTML: {e}")
                            logger.error(traceback.format_exc())
                            continue
                            
                    except Exception as e:
                        logger.error(f"Ошибка при обработке результата {i}: {e}")
                        logger.error(traceback.format_exc())
                        continue
                        
                await browser.close()
                logger.debug("Браузер закрыт")
            
            # Проверяем наличие HTML-контента
            results_with_html = sum(1 for r in results if r.get('html_content'))
            logger.info(f"\nРезультаты с HTML-контентом: {results_with_html}/{len(results)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Критическая ошибка при выполнении поиска: {e}")
            logger.error(traceback.format_exc())
            return [] 