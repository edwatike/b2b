import asyncio
import random
import logging
import os
import datetime
from typing import Optional, Dict, Any, List
from playwright.async_api import Page
from ..config.parser_config import config

logger = logging.getLogger(__name__)

class CaptchaSolver:
    """
    Класс для обнаружения и попыток обхода капчи
    """
    
    def __init__(self):
        """Инициализация обработчика капчи"""
        # Создаем директорию для скриншотов капчи, если ее нет
        os.makedirs(config.captcha_screenshot_path, exist_ok=True)
        self.detection_phrases = config.captcha_detection_phrases
        self.detection_selectors = [
            ".g-recaptcha",
            "iframe[src*='recaptcha']",
            "iframe[src*='captcha']",
            "div[class*='captcha']",
            "input[id*='captcha']",
            "div[id*='captcha']",
            "form[action*='captcha']",
            ".captcha-container",
            "#captcha",
            "button[id*='captcha']"
        ]
    
    async def is_captcha_present(self, page: Page) -> bool:
        """
        Проверяет наличие капчи на странице используя различные методы обнаружения
        """
        try:
            # Проверка по селекторам
            for selector in self.detection_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.warning(f"Обнаружена капча по селектору: {selector}")
                    return True
            
            # Проверка по ключевым словам в тексте страницы
            page_text = await page.text_content("body") or ""
            page_text = page_text.lower()
            
            for phrase in self.detection_phrases:
                if phrase.lower() in page_text:
                    logger.warning(f"Обнаружена капча по ключевому слову: {phrase}")
                    return True
                    
            # Проверка по наличию iframe от reCAPTCHA
            recaptcha_frames = await page.query_selector_all("iframe[src*='recaptcha'], iframe[src*='google.com/recaptcha']")
            if recaptcha_frames:
                logger.warning(f"Обнаружена reCAPTCHA (найдено {len(recaptcha_frames)} iframe)")
                return True
                
            # Дополнительная проверка - если страница содержит определенные URL в ресурсах
            captcha_resources = await page.evaluate("""() => {
                const captchaResources = [];
                
                if (typeof performance !== 'undefined' && performance.getEntriesByType) {
                    const resources = performance.getEntriesByType('resource');
                    for (const resource of resources) {
                        if (resource.name.includes('captcha') || 
                            resource.name.includes('recaptcha') ||
                            resource.name.includes('gstatic.com/recaptcha')) {
                            captchaResources.push(resource.name);
                        }
                    }
                }
                
                return captchaResources;
            }""")
            
            if captcha_resources and len(captcha_resources) > 0:
                logger.warning(f"Обнаружены ресурсы капчи: {captcha_resources}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке наличия капчи: {e}")
            return False
    
    async def save_captcha_screenshot(self, page: Page) -> Optional[str]:
        """
        Сохраняет скриншот страницы с капчей для анализа
        """
        try:
            timestamp = int(datetime.datetime.now().timestamp())
            filename = f"captcha_{timestamp}.png"
            filepath = os.path.join(config.captcha_screenshot_path, filename)
            
            await page.screenshot(path=filepath, full_page=True)
            
            # Также сохраняем HTML страницы для анализа
            html_filepath = os.path.join(config.captcha_screenshot_path, f"captcha_{timestamp}.html")
            html_content = await page.content()
            
            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            logger.info(f"Сохранен скриншот капчи: {filepath} и HTML-код")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении скриншота капчи: {e}")
            return None
    
    async def attempt_bypass(self, page: Page, max_attempts: int = 3) -> bool:
        """
        Пытается обойти капчу с помощью имитации человеческого поведения
        """
        from .human_like_behavior import HumanLikeBehavior
        human = HumanLikeBehavior(config)
        
        logger.info("Попытка обойти капчу с помощью имитации человеческого поведения")
        
        # Сохраняем скриншот для анализа
        await self.save_captcha_screenshot(page)
        
        # Пробуем несколько подходов к обходу
        for attempt in range(max_attempts):
            logger.info(f"Попытка обхода капчи #{attempt + 1}")
            
            try:
                # 1. Пробуем найти чекбокс "Я не робот" и кликнуть по нему
                checkbox_selectors = [
                    "div.recaptcha-checkbox-border",
                    ".recaptcha-checkbox-checkmark",
                    "#recaptcha-anchor",
                    "div[role='presentation']"
                ]
                
                for selector in checkbox_selectors:
                    try:
                        checkbox = await page.query_selector(selector)
                        if checkbox:
                            # Естественное движение к чекбоксу и клик
                            box = await checkbox.bounding_box()
                            if box:
                                # Имитируем естественное движение мыши и клик
                                await human.human_mouse_move(page, 
                                    box["x"] + box["width"] / 2 + random.uniform(-5, 5),
                                    box["y"] + box["height"] / 2 + random.uniform(-3, 3)
                                )
                                await asyncio.sleep(random.uniform(0.2, 0.7))
                                await page.mouse.click(
                                    box["x"] + box["width"] / 2 + random.uniform(-5, 5),
                                    box["y"] + box["height"] / 2 + random.uniform(-3, 3),
                                    delay=random.randint(50, 150)
                                )
                                logger.info(f"Успешно кликнули по чекбоксу капчи с селектором {selector}")
                                await asyncio.sleep(random.uniform(2.0, 4.0))
                                
                                # Проверяем, исчезла ли капча
                                if not await self.is_captcha_present(page):
                                    logger.info("Капча успешно обойдена через чекбокс")
                                    return True
                    except Exception as e:
                        logger.debug(f"Ошибка при работе с чекбоксом {selector}: {e}")
                
                # 2. Если есть фрейм с капчей, пытаемся переключиться на него
                recaptcha_frames = await page.query_selector_all("iframe[src*='recaptcha']")
                for i, frame in enumerate(recaptcha_frames):
                    try:
                        frame_handle = await frame.content_frame()
                        if frame_handle:
                            logger.info(f"Переключаемся на фрейм капчи #{i+1}")
                            
                            # Проверяем чекбоксы внутри фрейма
                            for selector in checkbox_selectors:
                                try:
                                    checkbox = await frame_handle.query_selector(selector)
                                    if checkbox:
                                        box = await checkbox.bounding_box()
                                        if box:
                                            await frame_handle.mouse.move(
                                                box["x"] + box["width"] / 2,
                                                box["y"] + box["height"] / 2
                                            )
                                            await asyncio.sleep(random.uniform(0.3, 0.8))
                                            await frame_handle.mouse.click(
                                                box["x"] + box["width"] / 2,
                                                box["y"] + box["height"] / 2,
                                                delay=random.randint(50, 150)
                                            )
                                            logger.info(f"Кликнули по чекбоксу внутри фрейма")
                                            
                                            # Ожидаем загрузки после клика
                                            await asyncio.sleep(random.uniform(3.0, 5.0))
                                            
                                            # Проверяем, исчезла ли капча
                                            if not await self.is_captcha_present(page):
                                                logger.info("Капча успешно обойдена через фрейм")
                                                return True
                                except Exception as e:
                                    logger.debug(f"Ошибка при работе с чекбоксом внутри фрейма: {e}")
                    except Exception as e:
                        logger.debug(f"Ошибка при работе с фреймом {i+1}: {e}")
                
                # 3. Имитация случайной активности пользователя
                # Движения мыши
                await human.random_mouse_movement(page, random.randint(3, 7))
                
                # Скроллинг
                await human.random_scroll_page(page, random.randint(2, 5))
                
                # Делаем паузу, как будто пользователь думает
                await human.take_break(5.0, 10.0)
                
                # Проверяем, исчезла ли капча после нашей активности
                if not await self.is_captcha_present(page):
                    logger.info("Капча исчезла после имитации пользовательской активности")
                    return True
                
                # 4. Проверяем, есть ли на странице кнопка обновления капчи
                refresh_selectors = [
                    ".recaptcha-refresh", 
                    "button[title*='new challenge']",
                    "button[title*='получить новую задачу']",
                    ".reload-button"
                ]
                
                for selector in refresh_selectors:
                    try:
                        refresh_button = await page.query_selector(selector)
                        if refresh_button:
                            box = await refresh_button.bounding_box()
                            if box:
                                # Имитируем естественное движение мыши и клик
                                await human.human_mouse_move(page, 
                                    box["x"] + box["width"] / 2,
                                    box["y"] + box["height"] / 2
                                )
                                await asyncio.sleep(random.uniform(0.2, 0.5))
                                await page.mouse.click(
                                    box["x"] + box["width"] / 2,
                                    box["y"] + box["height"] / 2
                                )
                                logger.info(f"Кликнули на кнопку обновления капчи")
                                await asyncio.sleep(random.uniform(2.0, 4.0))
                    except Exception as e:
                        logger.debug(f"Ошибка при работе с кнопкой обновления: {e}")
                
                # 5. Нажимаем Tab и Enter как способ навигации через клавиатуру 
                # (иногда помогает активировать чекбокс)
                for _ in range(random.randint(2, 5)):
                    await page.keyboard.press("Tab")
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                
                await page.keyboard.press("Enter")
                await asyncio.sleep(random.uniform(2.0, 3.0))
                
                # Проверяем результат
                if not await self.is_captcha_present(page):
                    logger.info("Капча обойдена с помощью клавиатурной навигации")
                    return True
                
                # Между попытками делаем паузу, чтобы не выглядеть как бот
                logger.info(f"Попытка #{attempt + 1} не удалась, делаем паузу перед следующей")
                await asyncio.sleep(random.uniform(5.0, 10.0))
                
            except Exception as e:
                logger.error(f"Ошибка при попытке обхода капчи #{attempt + 1}: {e}")
        
        logger.warning(f"Не удалось обойти капчу после {max_attempts} попыток")
        return False
    
    async def handle_captcha(self, page: Page) -> bool:
        """
        Комплексная обработка капчи - обнаружение и попытка обхода
        """
        # Проверяем наличие капчи
        if await self.is_captcha_present(page):
            logger.warning("Обнаружена капча, пытаемся обойти")
            
            # Сохраняем скриншот
            await self.save_captcha_screenshot(page)
            
            # Пытаемся обойти
            success = await self.attempt_bypass(page)
            
            if not success:
                # Если не удалось обойти, делаем длительную паузу и пробуем еще раз
                logger.info("Делаем длительную паузу и пробуем обойти капчу снова")
                await asyncio.sleep(random.uniform(
                    config.captcha_retry_min_delay,
                    config.captcha_retry_max_delay
                ))
                
                # Перезагружаем страницу
                await page.reload()
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
                # Проверяем, исчезла ли капча после перезагрузки и паузы
                if not await self.is_captcha_present(page):
                    logger.info("Капча исчезла после перезагрузки и паузы")
                    return True
                
                # Пробуем обойти еще раз после паузы
                success = await self.attempt_bypass(page)
            
            return success
        
        return True  # Капчи нет, все хорошо 

async def check_captcha(page: Page) -> bool:
    """
    Проверяет наличие капчи на странице.
    
    Args:
        page: Страница Playwright
        
    Returns:
        bool: True если обнаружена капча, иначе False
    """
    try:
        # Проверяем различные признаки капчи
        captcha_selectors = [
            "div.CheckboxCaptcha",
            "div.Captcha",
            "div.AdvancedCaptcha",
            "div.AdvancedCaptcha-View",
            "div.Captcha-View",
            "div.CheckboxCaptcha-View",
            "form[name='captcha']",
            "div[class*='captcha']",
            "div[class*='Captcha']"
        ]
        
        for selector in captcha_selectors:
            if await page.query_selector(selector):
                logger.warning("Обнаружена капча на странице")
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"Ошибка при проверке капчи: {str(e)}")
        return False 