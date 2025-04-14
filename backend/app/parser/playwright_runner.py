from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Playwright
import asyncio
import random
from typing import Optional, Dict, List, Tuple, Any
import logging
from .config.parser_config import config, ParserConfig
from .utils import random_delay, get_random_user_agent
from .helpers.captcha_solver import CaptchaSolver
from .helpers.human_like_behavior import HumanLikeBehavior
import datetime

logger = logging.getLogger(__name__)

class PlaywrightRunner:
    def __init__(self, config: ParserConfig):
        self.config = config
        self.browser_pool = []
        self.proxy_index = 0
        self.proxies = self._load_proxies()
        self.page_pool = []
        self.playwright = None
        self.captcha_solver = CaptchaSolver()
        self.human_behavior = None  # Будет инициализирован позже
        
    def _load_proxies(self) -> List[str]:
        """Load and validate proxies from config"""
        if not self.config.proxy_enabled:
            return []
        
        proxies = []
        for proxy in self.config.proxies:
            if proxy.startswith(('http://', 'https://')):
                proxies.append(proxy)
            else:
                proxies.append(f'http://{proxy}')
        
        if not proxies:
            logger.warning("No valid proxies found in config")
        return proxies

    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy from rotation"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

    async def _retry_with_new_proxy(self, page, url: str, max_retries: int = 3) -> bool:
        """Retry request with new proxy if captcha detected"""
        for attempt in range(max_retries):
            try:
                proxy = self._get_next_proxy()
                if not proxy:
                    logger.error("No proxies available for retry")
                    return False

                logger.info(f"Retrying with new proxy: {proxy}")
                await page.context.clear_cookies()
                await page.context.clear_storage()
                
                # Reinitialize browser with new proxy
                await self._init_browser(page.context, proxy)
                
                response = await page.goto(url, wait_until="networkidle")
                if response and response.status == 200:
                    if not await self._check_captcha(page):
                        return True
                
                await asyncio.sleep(random.uniform(2, 5))
            except Exception as e:
                logger.error(f"Proxy retry attempt {attempt + 1} failed: {str(e)}")
        
        return False

    async def _check_captcha(self, page) -> bool:
        """Enhanced captcha detection"""
        captcha_selectors = [
            "#captcha-form",
            "iframe[src*='recaptcha']",
            ".g-recaptcha",
            "form[action*='captcha']"
        ]
        
        for selector in captcha_selectors:
            if await page.locator(selector).count() > 0:
                logger.warning("Captcha detected on page")
                return True
        return False

    async def _human_like_typing(self, locator, text: str):
        """Enhanced human-like typing simulation"""
        await locator.click()
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        for char in text:
            # Random typing speed
            delay = random.uniform(50, 200)
            await locator.type(char, delay=delay)
            
            # Random backspace and corrections
            if random.random() < 0.1:
                await locator.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await locator.type(char, delay=delay)
            
            # Random pauses between words
            if char == " ":
                await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Final random pause before submitting
        await asyncio.sleep(random.uniform(0.5, 2))

    async def _human_like_mouse_movement(self, page, target):
        """Enhanced mouse movement simulation"""
        # Get current mouse position
        current_pos = await page.evaluate("""() => {
            return { x: window.mouseX || 0, y: window.mouseY || 0 };
        }""")
        
        # Get target position
        box = await target.bounding_box()
        if not box:
            return
        
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        
        # Generate multiple control points for more natural movement
        control_points = []
        steps = random.randint(3, 7)
        for i in range(steps):
            t = i / (steps - 1)
            x = current_pos["x"] + (target_x - current_pos["x"]) * t
            y = current_pos["y"] + (target_y - current_pos["y"]) * t
            # Add some randomness to the path
            x += random.uniform(-50, 50)
            y += random.uniform(-50, 50)
            control_points.append({"x": x, "y": y})
        
        # Move through control points
        for point in control_points:
            await page.mouse.move(point["x"], point["y"])
            await asyncio.sleep(random.uniform(0.01, 0.05))
        
        # Final movement to target
        await page.mouse.move(target_x, target_y)
        await asyncio.sleep(random.uniform(0.1, 0.3))

    async def initialize(self):
        """Initialize Playwright and create browser pool."""
        try:
            self.playwright = await async_playwright().start()
            self.human_behavior = HumanLikeBehavior(self.config)
            
            # Create browser instances
            for _ in range(self.config.browser_pool_size):
                # Select proxy if enabled
                proxy = None
                if self.config.proxy_enabled and self.proxies:
                    proxy = self._get_next_proxy()
                
                # Launch browser with appropriate settings
                browser = await self.playwright.chromium.launch(
                    headless=self.config.browser_headless,
                    proxy=proxy,
                    timeout=self.config.browser_timeout * 1000,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--disable-site-isolation-trials",
                        "--disable-web-security",
                        "--disable-notifications",
                        "--ignore-certificate-errors",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-infobars",
                        "--window-size=1920,1080",
                        "--start-maximized",
                        "--disable-extensions",
                        "--mute-audio",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas"
                    ]
                )
                self.browser_pool.append(browser)
                
                # Create and configure context for the page
                context = await browser.new_context(
                    viewport={"width": random.randint(1100, 1920), "height": random.randint(800, 1080)},
                    user_agent=get_random_user_agent(self.config.user_agents),
                    is_mobile=False,
                    has_touch=False,
                    locale=random.choice(["ru-RU", "en-US", "en-GB"]),
                    timezone_id=random.choice(["Europe/Moscow", "Europe/London", "America/New_York"]),
                    color_scheme=random.choice(["dark", "light", "no-preference"]),
                    device_scale_factor=random.choice([1, 1.25, 1.5, 2]),
                    geolocation={
                        "latitude": random.uniform(55.0, 56.0),
                        "longitude": random.uniform(37.0, 38.0)
                    },
                    permissions=["geolocation"]
                )
                
                # Добавляем более реалистичное поведение мыши
                await context.add_init_script("""
                    // Эмуляция человеческого поведения мыши
                    const originalMouseEvent = MouseEvent;
                    MouseEvent = function(type, init) {
                        const event = new originalMouseEvent(type, {
                            ...init,
                            clientX: init.clientX + (Math.random() * 2 - 1),
                            clientY: init.clientY + (Math.random() * 2 - 1),
                            screenX: init.screenX + (Math.random() * 2 - 1),
                            screenY: init.screenY + (Math.random() * 2 - 1)
                        });
                        return event;
                    };
                    
                    // Эмуляция человеческого поведения клавиатуры
                    const originalKeyboardEvent = KeyboardEvent;
                    KeyboardEvent = function(type, init) {
                        const event = new originalKeyboardEvent(type, {
                            ...init,
                            keyCode: init.keyCode + (Math.random() * 2 - 1),
                            which: init.which + (Math.random() * 2 - 1)
                        });
                        return event;
                    };
                    
                    // Добавляем случайные задержки при вводе
                    const originalSetTimeout = window.setTimeout;
                    window.setTimeout = function(callback, delay) {
                        if (typeof callback === 'function') {
                            const jitter = Math.random() * 100;
                            return originalSetTimeout(callback, delay + jitter);
                        }
                        return originalSetTimeout(callback, delay);
                    };
                """)
                
                # Ограничиваем загрузку ресурсов для повышения производительности и снижения сигнатуры
                await context.route("**/*", lambda route: route.abort() 
                                   if route.request.resource_type in ["font", "stylesheet", "image", "media"]
                                   and not "recaptcha" in route.request.url
                                   and not "gstatic" in route.request.url
                                   else route.continue_())
                
                # Disable WebDriver flag and add more advanced evasion techniques
                await context.add_init_script("""
                    // Override navigator properties to avoid detection
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
                    
                    // Chrome specific properties
                    window.chrome = { 
                        runtime: {},
                        app: { 
                            InstallState: 'hehe', 
                            RunningState: 'running', 
                            getDetails: function() { return {}; }, 
                            getIsInstalled: function() { return true; },
                            isInstalled: true 
                        },
                        webstore: { 
                            onInstallStageChanged: {}, 
                            onDownloadProgress: {} 
                        }, 
                        csi: function() { return {}; }, 
                        loadTimes: function() { return {}; } 
                    };
                    
                    // Add fake plugins to look more like a real browser
                    const fakePDF = { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' };
                    const fakePlugin1 = { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format' };
                    const fakePlugin2 = { name: 'Native Client', filename: 'internal-nacl-plugin', description: 'Native Client Executable' };
                    
                    Object.defineProperty(navigator, 'plugins', {
                      get: () => [fakePDF, fakePlugin1, fakePlugin2]
                    });
                    
                    // Fake audio and canvas fingerprinting
                    const audioContext = window.AudioContext || window.webkitAudioContext;
                    if (audioContext) {
                        const realCreateOscillator = audioContext.prototype.createOscillator;
                        audioContext.prototype.createOscillator = function() {
                            const oscillator = realCreateOscillator.apply(this, arguments);
                            const randomDetune = Math.random() * 10;
                            const realStart = oscillator.start;
                            oscillator.start = function() {
                                this.detune.value = randomDetune;
                                return realStart.apply(this, arguments);
                            };
                            return oscillator;
                        };
                    }
                    
                    // Override canvas fingerprinting
                    const originalGetContext = HTMLCanvasElement.prototype.getContext;
                    HTMLCanvasElement.prototype.getContext = function() {
                        const context = originalGetContext.apply(this, arguments);
                        if (context && arguments[0] === '2d') {
                            const originalFillText = context.fillText;
                            context.fillText = function() {
                                arguments[0] = arguments[0] + ' '; // slight change to font rendering
                                return originalFillText.apply(this, arguments);
                            };
                            
                            const originalGetImageData = context.getImageData;
                            context.getImageData = function() {
                                const imageData = originalGetImageData.apply(this, arguments);
                                // Alter a small part of the image data
                                if (imageData && imageData.data && imageData.data.length > 128) {
                                    for (let i = 0; i < 8; i++) {
                                        const offset = Math.floor(Math.random() * 128);
                                        const value = Math.floor(Math.random() * 16);
                                        imageData.data[offset] = (imageData.data[offset] + value) % 256;
                                    }
                                }
                                return imageData;
                            };
                        }
                        return context;
                    };
                    
                    // Add window dimensions variations
                    Object.defineProperty(window, 'innerWidth', {
                        get: function() { 
                            return this.innerWidthValue || Math.floor(Math.random() * 100) + 1024; 
                        }
                    });
                    Object.defineProperty(window, 'innerHeight', {
                        get: function() { 
                            return this.innerHeightValue || Math.floor(Math.random() * 100) + 768; 
                        }
                    });
                    
                    // WebGL fingerprint randomization
                    if (window.WebGLRenderingContext) {
                        const getParameter = WebGLRenderingContext.prototype.getParameter;
                        WebGLRenderingContext.prototype.getParameter = function(parameter) {
                            // Randomize parameters that are commonly used for fingerprinting
                            const fingerPrintParams = [37445, 37446, 37447];
                            if (fingerPrintParams.includes(parameter)) {
                                return Math.random() > 0.5 ? 'NVIDIA' : 'INTEL';
                            }
                            return getParameter.apply(this, arguments);
                        };
                    }
                    
                    // Fake navigator platform
                    Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                    
                    // Add permissions API mocking
                    if (!('permissions' in navigator)) {
                        navigator.permissions = {
                            query: function() {
                                return Promise.resolve({ state: 'granted' });
                            }
                        };
                    }
                    
                    // Override hardware concurrency
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => Math.floor(Math.random() * 8) + 4
                    });
                    
                    // Override device memory
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: () => Math.floor(Math.random() * 8) + 4
                    });
                """)
                
                # Create page
                page = await context.new_page()
                self.page_pool.append(page)
                
                # Setup browser-level evasion
                await self._setup_evasion_for_page(page)
                
            logger.info(f"Initialized {len(self.browser_pool)} browser instances")
            
        except Exception as e:
            logger.error(f"Error initializing Playwright: {e}")
            await self.cleanup()
            raise
            
    async def _setup_evasion_for_page(self, page: Page):
        """Setup additional evasion techniques for a page."""
        # Override permissions
        await page.context.grant_permissions(['geolocation'])
        
        # Random user-agent overrides on page level
        await page.evaluate("""() => {
            Object.defineProperty(navigator, 'userAgent', {
                get: () => window.navigator.userAgent
            });
        }""")
        
        # Add custom error handlers
        await page.route('**', lambda route: self._handle_request(route))
        
        # Add random cookies
        await self._set_random_cookies(page)
    
    async def _handle_request(self, route):
        """Handle requests with custom behavior to avoid detection."""
        request = route.request
        
        # If request is for known trackers or fingerprinting scripts, intercept
        if 'captcha' in request.url or 'recaptcha' in request.url:
            logger.info(f"Detected captcha request: {request.url}")
            
        # Continue with the request
        await route.continue_()
    
    async def _set_random_cookies(self, page: Page):
        """Set random cookies to appear more like a real user."""
        try:
            domain = "google.com"
            cookies = [
                {
                    "name": "CONSENT",
                    "value": f"YES+cb.{random.randint(10000000, 99999999)}",
                    "domain": ".google.com",
                    "path": "/",
                    "expires": int(random.random() * 10000000000),
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "None"
                },
                {
                    "name": f"NID",
                    "value": ''.join(random.choice('0123456789ABCDEF') for _ in range(64)),
                    "domain": ".google.com",
                    "path": "/",
                    "expires": int(random.random() * 10000000000),
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                },
                {
                    "name": "1P_JAR",
                    "value": f"{random.randint(2020, 2023)}-{random.randint(1, 12)}-{random.randint(1, 28)}-{random.randint(1, 23)}",
                    "domain": ".google.com",
                    "path": "/",
                    "expires": int(random.random() * 10000000000),
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "None"
                }
            ]
            
            await page.context.add_cookies(cookies)
            
        except Exception as e:
            logger.error(f"Error setting random cookies: {e}")
            
    async def get_page(self) -> Page:
        """Get available page from pool."""
        while True:
            for page in self.page_pool:
                if not getattr(page, '_in_use', False):
                    page._in_use = True
                    return page
            await asyncio.sleep(0.1)
            
    async def release_page(self, page: Page):
        """Release page back to pool."""
        # Clear cookies and storage to avoid tracking
        context = page.context
        await context.clear_cookies()
        await page.evaluate("""() => { 
            localStorage.clear(); 
            sessionStorage.clear(); 
        }""")
        page._in_use = False
    
    async def _human_like_scroll(self, page: Page):
        """Simulate human-like scrolling behavior."""
        # Get page height
        page_height = await page.evaluate("() => document.body.scrollHeight")
        viewport_height = await page.evaluate("() => window.innerHeight")
        
        # Scroll with randomness
        current_position = 0
        while current_position < page_height:
            # Random scroll distance
            scroll_distance = random.randint(100, 300)
            current_position += scroll_distance
            
            # Scroll with randomized speed
            await page.mouse.wheel(0, scroll_distance)
            
            # Random pauses during scrolling
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Small chance to scroll back up a bit (like a human looking for something)
            if random.random() < 0.2:
                await page.mouse.wheel(0, -random.randint(50, 150))
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
            # Very small chance to pause for longer
            if random.random() < 0.05:
                logger.info("Taking a longer pause during scrolling to appear more human-like")
                await asyncio.sleep(random.uniform(2.0, 4.0))
                
    async def _hover_and_move_randomly(self, page: Page):
        """Simulate random mouse movements and hovers."""
        viewport_size = await page.evaluate("""() => {
            return {
                width: window.innerWidth,
                height: window.innerHeight
            }
        }""")
        
        width = viewport_size["width"]
        height = viewport_size["height"]
        
        # Generate a natural-looking mouse movement path
        points = self._generate_mouse_path(
            (random.randint(0, width), random.randint(0, height)),
            (random.randint(0, width), random.randint(0, height)),
            5
        )
        
        for point in points:
            await page.mouse.move(point[0], point[1])
            await asyncio.sleep(random.uniform(0.01, 0.1))
            
        # Random chance to hover over a link or button
        links = await page.query_selector_all("a, button")
        if links and random.random() < 0.5:
            link = random.choice(links)
            await link.hover()
            await asyncio.sleep(random.uniform(0.5, 1.5))
    
    def _generate_mouse_path(self, start: Tuple[int, int], end: Tuple[int, int], steps: int) -> List[Tuple[int, int]]:
        """Generate a natural-looking mouse path with bezier curve."""
        # Generate control points for bezier curve
        control_point1 = (
            start[0] + (end[0] - start[0]) // 2 + random.randint(-100, 100),
            start[1] + (end[1] - start[1]) // 2 + random.randint(-100, 100)
        )
        
        path = []
        for i in range(steps + 1):
            t = i / steps
            # Quadratic bezier curve formula
            x = int((1 - t) * (1 - t) * start[0] + 2 * (1 - t) * t * control_point1[0] + t * t * end[0])
            y = int((1 - t) * (1 - t) * start[1] + 2 * (1 - t) * t * control_point1[1] + t * t * end[1])
            path.append((x, y))
        
        return path
        
    async def navigate(self, page: Page, url: str, max_retry_count: int = 3) -> Optional[str]:
        """Navigate to URL and return page content with human-like behavior."""
        retry_count = 0
        
        while retry_count < max_retry_count:
            try:
                logger.info(f"Переходим по URL: {url}")
                
                # Добавляем случайные куки перед каждой навигацией
                await self._set_random_cookies(page)
                
                # Эмуляция проверки истории
                if random.random() < 0.1:
                    # Иногда сначала переходим на стартовую страницу Google
                    start_url = "https://www.google.com/"
                    logger.info(f"Предварительный переход на {start_url}")
                    await page.goto(start_url, timeout=self.config.browser_timeout * 1000)
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    
                    # Выполняем случайные действия на странице
                    await self._human_like_scroll(page)
                    await asyncio.sleep(random.uniform(0.8, 2.0))
                
                # Случайная начальная задержка (естественная пауза перед переходом)
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # Устанавливаем заголовки с реальными значениями
                referer = random.choice([
                    "https://www.google.com/",
                    "https://mail.google.com/",
                    "",  # Иногда без реферера
                ])
                
                # Используем разнообразные значения заголовков
                await page.set_extra_http_headers({
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": random.choice(["ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7", "en-US,en;q=0.9,ru;q=0.8"]),
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate", 
                    "Sec-Fetch-Site": "none" if not referer else "same-origin",
                    "Sec-Fetch-User": "?1",
                    "Sec-Ch-Ua": "\"Google Chrome\";v=\"117\", \"Not;A=Brand\";v=\"8\"",
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": "\"Windows\"",
                    "Referer": referer
                })
                
                # Переходим по URL с таймаутом
                response = await page.goto(url, wait_until="networkidle", timeout=self.config.browser_timeout * 1000)
                
                if not response:
                    logger.error(f"Failed to get response for URL: {url}")
                    retry_count += 1
                    continue
                
                if response.status == 200:
                    # Проверяем наличие капчи
                    if await self._check_captcha(page):
                        logger.warning("Captcha detected during navigation")
                        if not await self._retry_with_new_proxy(page, url):
                            retry_count += 1
                            continue
                    
                    # Успешная навигация
                    return response
                else:
                    logger.error(f"Received status {response.status} for URL: {url}")
                    retry_count += 1
                    
            except Exception as e:
                logger.error(f"Error during navigation: {str(e)}")
                retry_count += 1
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
        logger.error(f"Failed to navigate to {url} after {max_retry_count} attempts")
        return None
    
    async def _simulate_human_page_viewing(self, page: Page):
        """Имитирует естественное поведение пользователя при просмотре страницы."""
        try:
            # Получаем размеры окна
            viewport = await page.evaluate("""() => {
                return {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    scrollHeight: document.body.scrollHeight
                }
            }""")
            
            # Проверяем, нужно ли прокручивать страницу
            if viewport["scrollHeight"] > viewport["height"]:
                # Начинаем с небольшой паузы, как будто пользователь оценивает страницу
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                # Прокручиваем страницу медленно с небольшими остановками
                current_scroll = 0
                target_scroll = min(viewport["scrollHeight"], 2000)  # Не прокручиваем всю страницу
                
                while current_scroll < target_scroll:
                    # Определяем размер прокрутки (меньше в начале и в конце)
                    progress = current_scroll / target_scroll
                    if progress < 0.2 or progress > 0.8:
                        scroll_amount = random.randint(50, 100)  # Медленнее в начале и конце
                    else:
                        scroll_amount = random.randint(100, 200)  # Быстрее в середине
                    
                    # Прокручиваем страницу
                    await page.mouse.wheel(0, scroll_amount)
                    current_scroll += scroll_amount
                    
                    # С некоторой вероятностью останавливаемся, чтобы "прочитать" содержимое
                    if random.random() < 0.3:
                        # Подвигаем мышь к случайному элементу на странице
                        elements = await page.query_selector_all('a, button, input, div, span')
                        if elements and len(elements) > 0:
                            random_element = random.choice(elements)
                            try:
                                box = await random_element.bounding_box()
                                if box:
                                    # Перемещаем мышь к элементу
                                    await self._natural_mouse_movement(
                                        page, 
                                        box["x"] + box["width"] / 2, 
                                        box["y"] + box["height"] / 2
                                    )
                                    
                                    # С небольшой вероятностью наводим на элемент (hover)
                                    if random.random() < 0.3:
                                        await random_element.hover()
                                        await asyncio.sleep(random.uniform(0.5, 1.5))
                            except:
                                pass
                        
                        # Делаем паузу, как будто читаем контент
                        await asyncio.sleep(random.uniform(1.0, 4.0))
                    else:
                        # Короткая пауза между прокрутками
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # С небольшой вероятностью прокручиваем обратно вверх
                if random.random() < 0.4:
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Иногда перемещаем курсор в случайную область страницы
            if random.random() < 0.5:
                await self._natural_mouse_movement(
                    page,
                    random.randint(50, viewport["width"] - 50),
                    random.randint(50, viewport["height"] - 50)
                )
                await asyncio.sleep(random.uniform(0.3, 1.0))
                
        except Exception as e:
            logger.error(f"Ошибка при имитации просмотра страницы: {e}")
    
    async def _is_captcha_present(self, page: Page) -> bool:
        """Проверяет наличие капчи на странице, используя более продвинутый класс CaptchaSolver."""
        return await self.captcha_solver.is_captcha_present(page)
            
    async def type_search_query(self, page: Page, query: str, selector: str):
        """Type a search query like a human would."""
        try:
            # Используем класс HumanLikeBehavior для более естественного ввода
            await self.human_behavior.human_type(page, selector, query)
            
            # Пауза перед нажатием Enter (как будто человек просматривает то, что набрал)
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            # Нажимаем Enter с задержкой
            await page.keyboard.press("Enter", delay=random.randint(50, 150))
            
            # Ожидаем начала загрузки
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
        except Exception as e:
            logger.error(f"Ошибка при вводе поискового запроса: {e}")
            
    async def _natural_mouse_movement(self, page: Page, target_x: float, target_y: float):
        """Имитирует естественное движение мыши к цели с замедлением и случайностью."""
        try:
            # Получаем текущую позицию мыши
            current_pos = await page.evaluate("""() => {
                return {x: 0, y: 0}; // Стартовая позиция (можно уточнить)
            }""")
            
            start_x = current_pos["x"]
            start_y = current_pos["y"]
            
            # Генерируем путь с естественными изгибами
            points = self._generate_bezier_curve(
                (start_x, start_y),
                (target_x, target_y),
                random.randint(5, 10)  # Случайное количество точек для более естественного движения
            )
            
            # Двигаем мышь по точкам с изменяющейся скоростью
            for i, (x, y) in enumerate(points):
                # Замедляем движение в начале и в конце (имитация ускорения и замедления)
                progress = i / len(points)
                if progress < 0.2 or progress > 0.8:
                    delay = random.uniform(0.01, 0.03)  # Медленнее в начале и конце
                else:
                    delay = random.uniform(0.005, 0.01)  # Быстрее в середине
                
                await page.mouse.move(x, y)
                await asyncio.sleep(delay)
                
            # Делаем последний шаг к цели
            await page.mouse.move(target_x, target_y)
            
        except Exception as e:
            logger.error(f"Ошибка при эмуляции движения мыши: {e}")
    
    def _generate_bezier_curve(self, start, end, num_points):
        """Генерирует кривую Безье для естественного движения мыши."""
        # Создаем случайную контрольную точку для изгиба кривой
        control_x = (start[0] + end[0]) / 2 + random.uniform(-100, 100)
        control_y = (start[1] + end[1]) / 2 + random.uniform(-100, 100)
        
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            # Квадратичная кривая Безье
            x = (1 - t) * (1 - t) * start[0] + 2 * (1 - t) * t * control_x + t * t * end[0]
            y = (1 - t) * (1 - t) * start[1] + 2 * (1 - t) * t * control_y + t * t * end[1]
            points.append((x, y))
        
        return points
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            for page in self.page_pool:
                try:
                    await page.close()
                except:
                    pass
            
            for browser in self.browser_pool:
                try:
                    await browser.close()
                except:
                    pass
                    
            if self.playwright:
                await self.playwright.stop()
                
            self.page_pool = []
            self.browser_pool = []
            self.playwright = None
            
            logger.info("Cleaned up Playwright resources")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def search_google(self, query: str, region: str = "не указан") -> List[Dict[str, Any]]:
        """Enhanced Google search with improved anti-detection"""
        page = await self._get_page_from_pool()
        if not page:
            return []

        try:
            # Clear all storage before new search
            await page.context.clear_cookies()
            await page.context.clear_storage()
            
            # Set random viewport and user agent
            await self._set_random_viewport(page)
            await self._set_random_user_agent(page)
            
            # Navigate to Google with retry logic
            success = await self._retry_with_new_proxy(page, "https://www.google.ru")
            if not success:
                return []

            # Enhanced human-like behavior
            await self._human_like_mouse_movement(page, page.locator('textarea[name="q"]'))
            await self._human_like_typing(page.locator('textarea[name="q"]'), query)
            
            # Random pause before submitting
            await asyncio.sleep(random.uniform(1, 3))
            
            # Submit search with random delay
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            
            # Check for captcha after submission
            if await self._check_captcha(page):
                logger.warning("Captcha detected after search submission")
                success = await self._retry_with_new_proxy(page, page.url)
                if not success:
                    return []

            # Enhanced result parsing with human-like scrolling
            results = await self._parse_search_results(page)
            
            # Random pause between pages
            await asyncio.sleep(random.uniform(2, 5))
            
            return results

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
        finally:
            await self._return_page_to_pool(page)

    async def _parse_search_results(self, page) -> List[Dict[str, Any]]:
        """Parse search results with enhanced human-like behavior"""
        results = []
        
        # Simulate reading behavior
        await self._simulate_reading_behavior(page)
        
        # Get all result elements
        result_elements = await page.locator('div[data-sokoban-container]').all()
        
        for element in result_elements:
            try:
                # Scroll to element with human-like behavior
                await self._human_like_scroll_to_element(page, element)
                
                # Extract result data
                title = await element.locator('h3').text_content()
                link = await element.locator('a').get_attribute('href')
                snippet = await element.locator('div[data-content-feature]').text_content()
                
                if title and link:
                    results.append({
                        'title': title.strip(),
                        'link': link.strip(),
                        'snippet': snippet.strip() if snippet else '',
                        'position': len(results) + 1
                    })
                
                # Random pause between results
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                logger.error(f"Error parsing result: {str(e)}")
                continue
        
        return results

    async def _simulate_reading_behavior(self, page):
        """Simulate natural reading behavior"""
        # Random scroll pauses
        scroll_pauses = random.randint(3, 7)
        for _ in range(scroll_pauses):
            # Scroll random amount
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 2))
            
            # Random mouse movements
            if random.random() < 0.3:
                await self._random_mouse_movement(page)
            
            # Random pauses
            if random.random() < 0.2:
                await asyncio.sleep(random.uniform(1, 3))

    async def _random_mouse_movement(self, page):
        """Make random mouse movements on the page"""
        viewport = await page.viewport_size()
        if not viewport:
            return
            
        for _ in range(random.randint(2, 5)):
            x = random.randint(0, viewport['width'])
            y = random.randint(0, viewport['height'])
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def _human_like_scroll_to_element(self, page, element):
        """Scroll to element with human-like behavior"""
        box = await element.bounding_box()
        if not box:
            return
            
        # Calculate scroll steps
        current_position = await page.evaluate("window.scrollY")
        target_position = box['y'] - 100  # Scroll to slightly above the element
        
        # Smooth scroll with random pauses
        steps = random.randint(3, 7)
        for i in range(steps):
            progress = i / (steps - 1)
            scroll_position = current_position + (target_position - current_position) * progress
            await page.evaluate(f"window.scrollTo(0, {scroll_position})")
            
            # Random pause during scroll
            if random.random() < 0.3:
                await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Final scroll to exact position
        await page.evaluate(f"window.scrollTo(0, {target_position})")
        await asyncio.sleep(random.uniform(0.2, 0.5))

    async def init_browser_context(self, playwright: Playwright) -> Tuple[Browser, BrowserContext]:
        """Инициализирует браузер и контекст с настроенными параметрами.
        
        Args:
            playwright: Экземпляр Playwright
            
        Returns:
            Tuple[Browser, BrowserContext]: Браузер и контекст
        """
        try:
            # Запускаем браузер
            browser = await playwright.chromium.launch(
                headless=self.config.headless
            )
            
            # Создаем контекст с настроенными параметрами
            context = await browser.new_context(
                user_agent=self.config.user_agent,
                proxy=self.config.get_random_proxy() if self.config.proxy_enabled else None,
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                geolocation={"latitude": 55.7558, "longitude": 37.6173},
                permissions=["geolocation"]
            )
            
            # Устанавливаем скрипты для обхода обнаружения
            await context.add_init_script("""
                // Переопределяем свойство webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                // Добавляем фейковые свойства для Chrome
                window.chrome = {
                    runtime: {}
                };
                
                // Эмулируем плагины
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        }
                    ]
                });
            """)
            
            return browser, context
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации браузера: {str(e)}")
            raise
            
    async def navigate(self, page: Page, url: str, timeout: int = None) -> bool:
        """Выполняет навигацию по URL с эмуляцией человеческого поведения.
        
        Args:
            page: Страница браузера
            url: URL для перехода
            timeout: Таймаут ожидания загрузки страницы
            
        Returns:
            bool: True, если навигация успешна
        """
        try:
            # Устанавливаем случайные куки
            await page.evaluate("""() => {
                document.cookie = `session_id=${Math.random().toString(36).substring(7)}`;
                document.cookie = `user_id=${Math.random().toString(36).substring(7)}`;
            }""")
            
            # Эмулируем человеческое поведение
            await self._simulate_human_behavior(page)
            
            # Добавляем случайную задержку перед переходом
            await asyncio.sleep(random.uniform(1, 3))
            
            # Устанавливаем заголовки запроса
            await page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "TE": "Trailers"
            })
            
            # Выполняем навигацию
            response = await page.goto(
                url,
                wait_until="networkidle",
                timeout=timeout or self.config.timeout
            )
            
            if not response:
                logger.error(f"Не удалось получить ответ при переходе на {url}")
                return False
                
            if not response.ok:
                logger.error(f"Ошибка при переходе на {url}: {response.status}")
                return False
                
            # Проверяем наличие капчи
            if await self._check_captcha(page):
                logger.warning(f"Обнаружена капча на {url}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при навигации на {url}: {str(e)}")
            return False
            
    async def _simulate_human_behavior(self, page: Page) -> None:
        """Эмулирует человеческое поведение на странице."""
        try:
            # Случайные движения мыши
            for _ in range(random.randint(3, 7)):
                await page.mouse.move(
                    random.randint(0, 1000),
                    random.randint(0, 1000)
                )
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
            # Случайный скролл
            await page.evaluate("""() => {
                window.scrollTo({
                    top: Math.random() * document.body.scrollHeight,
                    behavior: 'smooth'
                });
            }""")
            
            await asyncio.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.warning(f"Ошибка при эмуляции поведения: {str(e)}")
            
    async def _check_captcha(self, page: Page) -> bool:
        """Проверяет наличие капчи на странице."""
        try:
            # Проверяем различные селекторы капчи
            captcha_selectors = [
                "input[name='captcha']",
                ".captcha-wrapper",
                "#captcha",
                "img[alt*='captcha']",
                "div[class*='captcha']"
            ]
            
            for selector in captcha_selectors:
                if await page.query_selector(selector):
                    return True
                    
            return False
            
        except Exception as e:
            logger.warning(f"Ошибка при проверке капчи: {str(e)}")
            return False 