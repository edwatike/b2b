import random
import time
import asyncio
import math
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, Mouse
from ..config.parser_config import ParserConfig


class HumanLikeBehavior:
    """
    Класс для имитации человеческого поведения в браузере
    """
    
    def __init__(self, config: ParserConfig):
        self.config = config
    
    async def human_delay(self, min_delay: Optional[float] = None, max_delay: Optional[float] = None) -> None:
        """
        Имитация случайной задержки как у человека
        """
        min_delay = min_delay if min_delay is not None else self.config.min_delay
        max_delay = max_delay if max_delay is not None else self.config.max_delay
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def human_type(self, page: Page, selector: str, text: str) -> None:
        """
        Имитация человеческого набора текста с переменной скоростью и возможными ошибками
        """
        await page.click(selector)
        await self.human_delay(0.5, 1.0)  # Задержка перед началом набора
        
        for i, char in enumerate(text):
            # Вероятность опечатки
            if random.random() < self.config.typing_error_probability:
                # Имитируем опечатку, вводя неправильный символ
                wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                await page.type(selector, wrong_char, delay=random.randint(
                    self.config.typing_min_delay, 
                    self.config.typing_max_delay
                ))
                
                # Задержка перед исправлением опечатки
                await self.human_delay(0.1, self.config.typing_correction_delay)
                
                # Нажимаем backspace для удаления неправильного символа
                await page.keyboard.press('Backspace')
                await self.human_delay(0.1, 0.3)
            
            # Типируем правильный символ
            await page.type(selector, char, delay=random.randint(
                self.config.typing_min_delay, 
                self.config.typing_max_delay
            ))
            
            # Случайно делаем паузу между символами для большей естественности
            if random.random() < 0.1:
                await self.human_delay(0.1, 0.7)
    
    def _bezier_curve(self, t: float, p0: float, p1: float, p2: float, p3: float) -> float:
        """
        Вычисление точки на кривой Безье 3-й степени
        """
        return (
            (1-t)**3 * p0 +
            3 * (1-t)**2 * t * p1 +
            3 * (1-t) * t**2 * p2 +
            t**3 * p3
        )
    
    async def human_mouse_move(self, page: Page, target_x: int, target_y: int) -> None:
        """
        Имитация человеческого движения мыши по кривой Безье
        """
        # Получаем текущее положение мыши
        mouse = page.mouse
        current_position = await page.evaluate("() => { return {x: window.mousePosX || 0, y: window.mousePosY || 0} }")
        start_x, start_y = current_position.get("x", 0), current_position.get("y", 0)
        
        # Создаем контрольные точки для кривой Безье
        # P0 - начальная точка (текущее положение)
        # P3 - конечная точка (целевое положение)
        # P1 и P2 - контрольные точки для создания естественной кривой
        
        # Вычисляем расстояние между точками
        distance = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
        
        # Делаем искривление кривой пропорциональным расстоянию
        curvature = min(distance * 0.3, 100)
        
        # Создаем контрольные точки с некоторой случайностью
        control_x1 = start_x + (target_x - start_x) * 0.3 + random.uniform(-curvature, curvature)
        control_y1 = start_y + (target_y - start_y) * 0.1 + random.uniform(-curvature, curvature)
        
        control_x2 = start_x + (target_x - start_x) * 0.7 + random.uniform(-curvature, curvature)
        control_y2 = start_y + (target_y - start_y) * 0.9 + random.uniform(-curvature, curvature)
        
        # Количество точек для движения (больше точек - более плавное движение)
        steps = self.config.mouse_move_points
        
        for i in range(steps + 1):
            t = i / steps
            
            # Вычисляем точку на кривой Безье
            x = self._bezier_curve(t, start_x, control_x1, control_x2, target_x)
            y = self._bezier_curve(t, start_y, control_y1, control_y2, target_y)
            
            # Выполняем движение мыши к промежуточной точке
            await mouse.move(x, y)
            
            # Сохраняем текущее положение мыши в глобальных переменных JavaScript
            await page.evaluate(f"window.mousePosX = {x}; window.mousePosY = {y};")
            
            # Добавляем небольшую случайную задержку для имитации человеческого движения
            await self.human_delay(
                self.config.mouse_move_min_delay, 
                self.config.mouse_move_max_delay
            )
    
    async def human_click(self, page: Page, selector: str) -> None:
        """
        Имитация человеческого клика с движением мыши
        """
        # Получаем координаты элемента
        element_box = await page.get_bounding_box(selector)
        if not element_box:
            raise ValueError(f"Element with selector {selector} not found")
        
        # Выбираем случайную точку внутри элемента для клика
        width, height = element_box["width"], element_box["height"]
        x_offset = random.uniform(10, max(width - 10, 11))
        y_offset = random.uniform(5, max(height - 5, 6))
        
        target_x = element_box["x"] + x_offset
        target_y = element_box["y"] + y_offset
        
        # Имитируем человеческое движение мыши к элементу
        await self.human_mouse_move(page, target_x, target_y)
        
        # Задержка перед кликом
        await self.human_delay(
            self.config.click_min_delay / 1000, 
            self.config.click_max_delay / 1000
        )
        
        # Выполняем клик
        await page.mouse.click(target_x, target_y)
    
    async def human_scroll(self, page: Page, direction: str = "down", distance: Optional[int] = None) -> None:
        """
        Имитация человеческого скроллинга страницы
        direction: "up" или "down"
        distance: если указано, прокручиваем на указанное расстояние, иначе случайное
        """
        if distance is None:
            # Случайное расстояние скролла
            distance = random.randint(
                self.config.scroll_step_min, 
                self.config.scroll_step_max
            )
        
        # Определяем направление скролла
        if direction == "up":
            distance = -distance
        
        # Производим скролл с задержкой
        await page.evaluate(f"window.scrollBy(0, {distance})")
        
        # Случайная задержка после скролла
        await self.human_delay(
            self.config.scroll_min_delay, 
            self.config.scroll_max_delay
        )
    
    async def random_scroll_page(self, page: Page, max_scrolls: int = 10) -> None:
        """
        Имитация случайного скроллинга по странице, как будто человек просматривает контент
        """
        scroll_count = random.randint(3, max_scrolls)
        
        for _ in range(scroll_count):
            # Определяем случайное направление (в основном вниз, но иногда и вверх)
            direction = "down" if random.random() < 0.8 else "up"
            
            await self.human_scroll(page, direction)
            
            # Случайная задержка между скроллами, имитирующая чтение контента
            await self.human_delay(0.5, 4.0)
    
    async def random_mouse_movement(self, page: Page, iterations: int = 3) -> None:
        """
        Имитация случайных движений мыши по странице
        """
        # Получаем размеры видимой области страницы
        viewport_size = await page.evaluate("""
            () => {
                return {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            }
        """)
        
        width, height = viewport_size["width"], viewport_size["height"]
        
        for _ in range(iterations):
            # Генерируем случайную точку в пределах экрана
            target_x = random.randint(0, width)
            target_y = random.randint(0, height)
            
            # Имитируем движение мыши к точке
            await self.human_mouse_move(page, target_x, target_y)
            
            # Случайная задержка между движениями
            await self.human_delay(0.3, 1.5)
    
    async def take_break(self, min_seconds: float = 5.0, max_seconds: float = 15.0) -> None:
        """
        Имитация перерыва, когда пользователь на время прекращает активность
        """
        break_time = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(break_time) 