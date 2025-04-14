#!/usr/bin/env python
import os
import asyncio
import logging
import traceback
from datetime import datetime

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("docker_test")

# Проверяем текущий каталог
logger.info(f"Текущий каталог: {os.getcwd()}")

# Импортируем модули
try:
    logger.info("Импортируем модули...")
    from playwright.async_api import async_playwright
    logger.info("✅ Модуль playwright успешно импортирован")
except Exception as e:
    logger.error(f"❌ Ошибка при импорте playwright: {e}")
    logger.error(traceback.format_exc())

async def main():
    """Тестовый скрипт для запуска в Docker"""
    logger.info("Запускаем тестовый скрипт в Docker")
    
    try:
        # Инициализация Playwright
        logger.info("Инициализация Playwright...")
        async with async_playwright() as playwright:
            logger.info("✅ Playwright запущен")
            
            # Запуск браузера
            logger.info("Запускаем браузер...")
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
            
            # Делаем скриншот начальной страницы
            await page.screenshot(path="/tmp/google_start_docker.png")
            logger.info("✅ Сохранен скриншот начальной страницы в /tmp/google_start_docker.png")
            
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
                await page.screenshot(path="/tmp/google_results_docker.png", full_page=True)
                logger.info("✅ Сохранен скриншот результатов в /tmp/google_results_docker.png")
                
                # Сохраняем HTML
                content = await page.content()
                with open("/tmp/google_results_docker.html", "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"✅ HTML сохранен в /tmp/google_results_docker.html (размер: {len(content)} байт)")
                
                # Извлекаем результаты
                logger.info("Извлекаем результаты поиска из HTML...")
                
                # Ищем результаты
                elements = await page.query_selector_all('div.tF2Cxc a')
                logger.info(f"Найдено {len(elements)} результатов")
                
                for i, element in enumerate(elements[:5]):
                    href = await element.get_attribute("href")
                    title_element = await element.query_selector("h3")
                    title = await title_element.inner_text() if title_element else ""
                    logger.info(f"Результат #{i+1}: {title} - {href}")
                
            else:
                logger.error("❌ Не удалось найти поле ввода")
            
            # Закрываем браузер
            logger.info("Закрываем браузер...")
            await browser.close()
            logger.info("✅ Браузер закрыт")
    
    except Exception as e:
        logger.error(f"❌ Ошибка при выполнении теста: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info(f"Запуск скрипта: {datetime.now()}")
    asyncio.run(main())
    logger.info(f"Завершение скрипта: {datetime.now()}") 