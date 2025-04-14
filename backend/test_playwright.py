#!/usr/bin/env python3
import os
import sys
import logging
import asyncio
from playwright.async_api import async_playwright

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("playwright_test")

async def main():
    logger.info("🔄 Запускаем тестовый скрипт Playwright")
    
    # Инициализация Playwright
    logger.info("Инициализация Playwright...")
    async with async_playwright() as playwright:
        logger.info("✅ Playwright запущен")
        
        # Запуск браузера в видимом режиме для отладки
        logger.info("Запускаем браузер (headless=False для отладки)...")
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=1920,1080"
            ]
        )
        logger.info("✅ Браузер запущен")
        
        # Создание контекста браузера
        logger.info("Создаем контекст браузера...")
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        logger.info("✅ Контекст создан")
        
        # Создание новой страницы
        logger.info("Создаем новую страницу...")
        page = await context.new_page()
        logger.info("✅ Страница создана")
        
        # Переход на Google
        logger.info("Переходим на Google...")
        await page.goto("https://www.google.ru", wait_until="networkidle")
        logger.info("✅ Страница Google загружена")
        
        # Сделаем скриншот начальной страницы
        await page.screenshot(path="/tmp/google_start.png")
        logger.info("✅ Сохранен скриншот начальной страницы в /tmp/google_start.png")
        
        # Ввод поискового запроса
        search_query = "шпунт ларсена"
        logger.info(f"Вводим поисковый запрос: '{search_query}'")
        
        # Находим поле ввода
        search_box = await page.query_selector("textarea[name='q']")
        if search_box:
            logger.info("✅ Найдено поле ввода")
            # Вводим запрос по символам
            for char in search_query:
                await page.type("textarea[name='q']", char, delay=100)
            
            # Нажимаем Enter
            await page.press("textarea[name='q']", "Enter")
            logger.info("✅ Нажали Enter")
            
            # Ожидаем загрузки результатов
            logger.info("Ожидаем загрузки результатов...")
            await page.wait_for_load_state("networkidle", timeout=30000)
            logger.info("✅ Страница результатов загружена")
            
            # Делаем скриншот страницы результатов
            await page.screenshot(path="/tmp/google_results.png", full_page=True)
            logger.info("✅ Сохранен скриншот результатов в /tmp/google_results.png")
            
            # Сохраняем HTML
            content = await page.content()
            with open("/tmp/google_results.html", "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"✅ HTML сохранен в /tmp/google_results.html (размер: {len(content)} байт)")
            
            # Извлекаем результаты
            logger.info("Извлекаем результаты поиска из HTML...")
            
            # Проверяем различные селекторы
            selectors = [
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
            
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                logger.info(f"Селектор '{selector}': найдено {len(elements)} элементов")
                
                for i, element in enumerate(elements[:5]):  # Выводим только первые 5
                    href = await element.get_attribute("href") 
                    text = await element.inner_text()
                    logger.info(f"  📌 Результат #{i+1}: href={href}, text={text}")
            
            # Задержка перед закрытием для просмотра
            await asyncio.sleep(3)
        else:
            logger.error("❌ Не удалось найти поле ввода")
        
        # Закрываем браузер
        logger.info("Закрываем браузер...")
        await browser.close()
        logger.info("✅ Браузер закрыт")

if __name__ == "__main__":
    asyncio.run(main()) 