from typing import List, Optional
from pydantic import BaseModel
import os

class ParserConfig(BaseModel):
    """Конфигурация парсера."""
    
    # Настройки браузера
    headless: bool = True
    proxy_enabled: bool = False
    proxy_list: List[str] = []
    
    # Настройки поиска
    max_retries: int = 3
    timeout: int = 120000
    max_results_per_page: int = 10
    
    # User-Agent
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # Задержки
    min_delay: int = 2
    max_delay: int = 5
    typing_delay: int = 100
    
    # Настройки поиска
    max_results: int = 1000
    search_mode: str = os.getenv("SEARCH_MODE", "both")  # yandex, google или both
    
    # Настройки прокси
    use_proxy: bool = False
    proxies: List[str] = []
    
    # Настройки эмуляции поведения
    enable_human_like_behavior: bool = True
    scroll_delay: tuple = (1, 3)  # Случайная задержка между скроллами
    mouse_movement_delay: tuple = (0.5, 1.5)  # Случайная задержка между движениями мыши
    
    # Настройки логирования
    enable_debug_logging: bool = True
    save_screenshots: bool = True
    screenshot_path: str = "/app/debug_screenshots"
    
    # Настройки прокси
    def get_random_proxy(self) -> Optional[str]:
        """Возвращает случайный прокси из списка."""
        if not self.proxy_enabled or not self.proxy_list:
            return None
        
        from random import choice
        return choice(self.proxy_list)

    def validate(self):
        """Проверяет корректность настроек."""
        valid_modes = ["yandex", "google", "both"]
        if self.search_mode not in valid_modes:
            raise ValueError(f"Недопустимый режим поиска. Допустимые значения: {valid_modes}")
            
        if self.max_results < 1:
            raise ValueError("Максимальное количество результатов должно быть больше 0")
            
        if self.timeout < 30000:
            raise ValueError("Таймаут браузера должен быть не менее 30 секунд") 