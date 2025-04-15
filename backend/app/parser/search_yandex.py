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

async def search_yandex(query: str, limit: int = 10, pages: int = 1) -> List[Dict]:
    """
    Выполняет поиск в Яндексе с использованием Playwright.
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов
        pages: Количество страниц для парсинга
        
    Returns:
        Список словарей с результатами поиска
    """
    logger.info(f"Начинаем поиск по запросу: {query} на {pages} страницах")
    results = []
    
    try:
        # Инициализируем Playwright
        async with async_playwright() as playwright:
            logger.info("Инициализация браузера...")
            browser, context = await init_browser_context(playwright)
            page = await context.new_page()
            
            try:
                for page_num in range(pages):
                    # Формируем URL для поиска с учетом номера страницы
                    search_url = f"https://yandex.ru/search/?text={urllib.parse.quote_plus(query)}&p={page_num}"
                    logger.info(f"Страница {page_num + 1}/{pages}: {search_url}")
                    
                    # Эмулируем поведение пользователя перед переходом на страницу
                    logger.info("Эмуляция поведения пользователя...")
                    await random_delay(2, 4)
                    await random_mouse_movement(page)
                    
                    # Переходим на страницу поиска
                    logger.info(f"Переход на страницу поиска: {search_url}")
                    response = await page.goto(search_url, wait_until="networkidle")
                    logger.info(f"Статус ответа: {response.status}")
                    
                    # Проверяем на наличие капчи
                    logger.info("Проверка на наличие капчи...")
                    if await check_captcha(page):
                        logger.warning("Обнаружена капча, пропускаем страницу")
                        continue
                    
                    # Делаем скриншот для диагностики
                    logger.info("Сохранение скриншота...")
                    await page.screenshot(path=f"/app/debug_screenshot_page_{page_num + 1}.png")
                    
                    # Ждем загрузки результатов
                    logger.info("Ожидание загрузки результатов...")
                    await page.wait_for_selector(".serp-item", timeout=30000)
                    
                    # Извлекаем результаты
                    logger.info("Извлечение результатов...")
                    items = await page.query_selector_all(".serp-item")
                    logger.info(f"Найдено элементов на странице {page_num + 1}: {len(items)}")
                    
                    for item in items:
                        try:
                            title_elem = await item.query_selector(".organic__url-text")
                            link_elem = await item.query_selector(".path a")
                            
                            if title_elem and link_elem:
                                title = await title_elem.text_content()
                                href = await link_elem.get_attribute("href")
                                
                                if title and href:
                                    logger.info(f"Найден результат: {title} -> {href}")
                                    results.append({
                                        "title": title.strip(),
                                        "url": href,
                                        "result_url": href
                                    })
                                    
                                    # Если достигли лимита, прекращаем сбор
                                    if len(results) >= limit:
                                        logger.info(f"Достигнут лимит результатов ({limit})")
                                        return results[:limit]
                        except Exception as e:
                            logger.error(f"Ошибка при обработке элемента: {str(e)}")
                            continue
                    
                    # Добавляем задержку между страницами
                    await random_delay(3, 5)
                
            finally:
                await context.close()
                await browser.close()
                
            logger.info(f"Поиск завершен. Найдено результатов: {len(results)}")
            
    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {str(e)}")
        raise
    
    return results[:limit]
