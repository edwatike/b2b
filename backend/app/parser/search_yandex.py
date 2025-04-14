from typing import List, Optional, Dict
import asyncio
import random
import logging
from datetime import datetime
from fake_useragent import UserAgent
from playwright.async_api import async_playwright, Browser, Page, Response
from app.parser.playwright_runner import PlaywrightRunner
from app.parser.helpers.human_like_behavior import (
    random_scroll,
    random_mouse_movement,
    random_delay
)
from app.parser.helpers.captcha_solver import check_captcha
import urllib.parse

logger = logging.getLogger(__name__)

# Список прокси для ротации
PROXY_LIST = []  # Отключаем использование прокси

async def init_browser_context(playwright, proxy: Optional[str] = None):
    """
    Инициализирует контекст браузера с расширенными настройками анти-детекта.
    """
    browser_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-automation',
        '--disable-dev-shm-usage',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-site-isolation-trials'
    ]
    
    try:
        browser = await playwright.chromium.launch(
            headless=True,
            args=browser_args
        )
        
        # Базовые настройки контекста
        context_settings = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
            "geolocation": {"latitude": 55.7558, "longitude": 37.6173},  # Москва
            "permissions": ["geolocation"],
            "java_script_enabled": True,
            "ignore_https_errors": True,
            "bypass_csp": True
        }
        
        if proxy:
            context_settings["proxy"] = {"server": proxy}
            
        context = await browser.new_context(**context_settings)
        
        # Устанавливаем дополнительные заголовки
        await context.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        })
        
        return browser, context
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации браузера: {str(e)}")
        raise

async def search_yandex(query: str, limit: int = 100) -> List[Dict[str, str]]:
    """
    Выполняет поиск в Яндексе и возвращает результаты с HTML-контентом.
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов
        
    Returns:
        List[Dict[str, str]]: Список результатов поиска
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            results = []
            page_num = 0
            
            while len(results) < limit:
                # Формируем URL для текущей страницы
                search_url = f"https://yandex.ru/search/?text={query}&p={page_num}"
                logger.info(f"Fetching page {page_num + 1} from: {search_url}")
                
                # Загружаем страницу
                await page.goto(search_url)
                await page.wait_for_selector('.serp-item')
                
                # Получаем результаты на странице
                items = await page.query_selector_all('.serp-item')
                
                if not items:
                    break
                    
                for item in items:
                    if len(results) >= limit:
                        break
                        
                    try:
                        # Получаем ссылку и заголовок
                        link_elem = await item.query_selector('a.link')
                        if not link_elem:
                            continue
                            
                        url = await link_elem.get_attribute('href')
                        title = await link_elem.inner_text()
                        
                        if not url:
                            continue
                            
                        # Получаем HTML-контент страницы
                        try:
                            result_page = await browser.new_page()
                            await result_page.goto(url, timeout=30000)
                            html_content = await result_page.content()
                            await result_page.close()
                        except Exception as e:
                            logger.error(f"Error fetching content from {url}: {e}")
                            html_content = ""
                        
                        # Добавляем результат
                        results.append({
                            'url': url,
                            'title': title,
                            'html_content': html_content
                        })
                        
                        logger.info(f"Added result: {url}")
                        
                    except Exception as e:
                        logger.error(f"Error processing search result: {e}")
                        continue
                
                page_num += 1
                
                # Добавляем задержку между запросами
                await asyncio.sleep(random.uniform(1, 3))
            
            await browser.close()
            return results
            
    except Exception as e:
        logger.error(f"Error in search_yandex: {e}")
        return []
