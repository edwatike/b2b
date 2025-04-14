from typing import List, Optional
from pydantic import BaseModel

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
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    # Задержки
    min_delay: int = 2
    max_delay: int = 5
    typing_delay: int = 100
    
    # Настройки прокси
    def get_random_proxy(self) -> Optional[str]:
        """Возвращает случайный прокси из списка."""
        if not self.proxy_enabled or not self.proxy_list:
            return None
        
        from random import choice
        return choice(self.proxy_list) 