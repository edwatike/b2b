from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ProxyConfig(BaseModel):
    server: str
    username: Optional[str] = None
    password: Optional[str] = None

class ParserConfig(BaseModel):
    # Browser pool settings
    browser_pool_size: int = 3  # Увеличиваем пул браузеров для масштабируемости
    browser_timeout: int = 30  # Увеличил таймаут для предотвращения ошибок при загрузке
    browser_headless: bool = True  # True для продакшн, False для отладки
    
    # Network and request management
    request_timeout: int = 30  # Таймаут для HTTP запросов
    max_concurrent_requests: int = 3  # Ограничение одновременных запросов для избежания блокировок
    request_delay: float = 2.0  # Задержка между запросами
    
    # Search settings
    search_depth: int = 3  # Number of search pages to parse
    results_per_page: int = 10
    search_url: str = "https://www.google.ru/"  # Используем Google
    
    # Human simulation settings
    min_delay: float = 1.8  # Увеличил минимальную задержку
    max_delay: float = 6.0  # Увеличил максимальную задержку
    typing_min_delay: int = 80  # Более реалистичные задержки между нажатиями клавиш
    typing_max_delay: int = 200
    scroll_min_delay: float = 0.5  # Более медленный скроллинг
    scroll_max_delay: float = 2.0
    scroll_step_min: int = 50  # Меньшие шаги скролла (более естественно)
    scroll_step_max: int = 150
    
    # Максимальное количество повторных попыток при получении капчи
    max_captcha_retries: int = 3
    
    # Задержки между попытками при получении капчи (в секундах)
    captcha_retry_min_delay: int = 10
    captcha_retry_max_delay: int = 30
    
    # Настройки повторных попыток при превышении лимита запросов (429 ошибка)
    max_429_retries: int = 3
    retry_429_min_delay: float = 60.0
    retry_429_max_delay: float = 300.0
    
    # Captcha handling and detection
    captcha_screenshot_path: str = "/tmp/captcha_screenshots/"
    captcha_detection_phrases: List[str] = [
        "captcha", "robot", "человек", "проверка", "подтвердите", 
        "проверьте", "не робот", "recaptcha", "верификация"
    ]
    
    # Request headers - extensive list of realistic user agents
    user_agents: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    
    # Популярные разрешения экрана
    screen_sizes: List[Dict[str, int]] = [
        {"width": 1920, "height": 1080},  # Full HD (наиболее распространенное)
        {"width": 1366, "height": 768},   # Типичный ноутбук
        {"width": 2560, "height": 1440},  # QHD
        {"width": 1440, "height": 900},   # Типичный MacBook
        {"width": 1536, "height": 864},   # Распространённое разрешение ноутбуков Windows
        {"width": 3840, "height": 2160},  # 4K
    ]
    
    # Locale settings
    supported_languages: List[str] = ["ru-RU", "en-US", "en-GB", "ru", "en"]
    supported_timezones: List[str] = ["Europe/Moscow", "Europe/London", "America/New_York", "Europe/Berlin", "Europe/Paris"]
    
    # Имитация различных устройств
    device_scale_factors: List[float] = [1.0, 1.25, 1.5, 2.0, 2.5]
    
    # Proxy settings - list of proxy servers to rotate through
    proxy_enabled: bool = False
    proxies: List[str] = []
    
    # Клик с задержкой для имитации человеческого поведения
    click_min_delay: int = 50  # минимальная задержка клика в мс
    click_max_delay: int = 150  # максимальная задержка клика в мс
    
    # Mouse behavior settings
    mouse_move_points: int = 10  # Количество точек для кривой Безье при движении мыши
    mouse_move_min_delay: float = 0.005  # Минимальная задержка между точками движения мыши
    mouse_move_max_delay: float = 0.03  # Максимальная задержка
    
    # Human typing behavior
    typing_error_probability: float = 0.05  # Вероятность опечатки
    typing_correction_delay: float = 0.5  # Задержка перед исправлением опечатки
    
    # Resource limitation - что блокировать для ускорения
    block_resources: List[str] = ["font", "stylesheet", "image", "media"]
    allow_domains: List[str] = ["google.com", "google.ru", "gstatic.com", "recaptcha.net"]
    
    # Parsing settings
    email_patterns: List[str] = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        r'mailto:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    ]
    
    phone_patterns: List[str] = [
        r'\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
        r'8[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    ]
    
    # URLs and domains to skip during parsing
    skip_domains: List[str] = [
        'youtube.com',
        'facebook.com',
        'instagram.com',
        'wikipedia.org',
        'twitter.com',
        'linkedin.com',
        'pinterest.com',
        'vk.com',
        'ok.ru',
        'google.com',
        'google.ru',
        'yandex.ru',
        'mail.ru',
        'amazon.com',
        'tiktok.com',
        'telegram.org',
        'youtube-nocookie.com',
        'googleadservices.com',
        'doubleclick.net',
        'google-analytics.com'
    ]

# Create the config instance
config = ParserConfig() 