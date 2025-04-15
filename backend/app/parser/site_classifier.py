import os
import re
import logging
import aiohttp
import asyncio
from urllib.parse import urlparse
from typing import Dict, Set, List, Tuple, Optional

logger = logging.getLogger(__name__)

class SiteClassifier:
    """Класс для классификации сайтов и их распределения по категориям."""
    
    def __init__(self):
        """Инициализирует объект классификатора."""
        # Списки известных агрегаторов, маркетплейсов и других подобных платформ
        self.aggregators = {
            'avito.ru', 'youla.ru', 'ozon.ru', 'ozon.by', 'wildberries.ru', 'wildberries.by', 
            'tiu.ru', 'prom.ua', 'yandex.ru', 'marketpapa.ru', 'aliexpress.ru', 'yandex.market', 
            'market.yandex.ru', 'lenta.com', 'yamarket.ru', 'sbermegamarket.ru', 'vseinstrumenti.ru',
            'goods.ru', 'megamarket.ru', 'dns-shop.ru', 'mvideo.ru', 'eldorado.ru', 'citilink.ru', 
            'onlinetrade.ru', 'lamoda.ru', 'sbermarket.ru', 'aliexpress.com', 'amazon.com', 
            'ebay.com', 'joom.com', 'toutiao.com', 'vk.com', 'ok.ru', 'facebook.com', 'instagram.com', 
            'telegram.org', 'twitter.com', 'youtube.com', 'tiktok.com', 'pinterest.com',
            'wikipedia.org', 'ruwiki.ru', 'livejournal.com', 'liveinternet.ru', 'pikabu.ru',
            'habr.com', 'vc.ru', 'blog.', 'medium.com', 'livejournal.', 'wordpress.', 'blogspot.',
            'forum.', 'forumhouse.ru'
        }
        
        # Паттерны для определения компаний-поставщиков
        self.supplier_patterns = r'\b(ИНН|ООО|ИП|ОАО|АО|ОГРН|ЗАО|НКО|ПК|ТОО|ЕООД|КФХ|СПК|ТСЖ|ТСН|МУП|ГУП|ФГУП|ФКП)\b'
        
        # Кэш уже проверенных доменов и их классификации
        self.domain_cache: Dict[str, str] = {}
        
        # Множество уже проверенных доменов для избежания дублирования
        self.processed_domains: Set[str] = set()
        
        # Результаты классификации
        self.suppliers: List[Dict] = []
        self.others: List[Dict] = []
        
        # Статистика
        self.stats = {
            'total_processed': 0,
            'suppliers_found': 0,
            'others_found': 0,
            'already_processed': 0,
            'errors': 0
        }
    
    async def classify_site(self, url: str, title: str = "", timeout: int = 10) -> Optional[str]:
        """
        Классифицирует сайт как поставщик или другой тип сайта.
        
        Args:
            url: URL сайта для классификации
            title: Заголовок страницы (если известен)
            timeout: Таймаут запроса в секундах
            
        Returns:
            str: 'supplier' или 'other' или None в случае ошибки
        """
        try:
            # Получаем домен из URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Удаляем www. из домена, если есть
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Проверяем, обрабатывался ли уже этот домен
            if domain in self.processed_domains:
                logger.info(f"Домен {domain} уже был обработан ранее")
                self.stats['already_processed'] += 1
                return self.domain_cache.get(domain)
            
            # Проверяем, является ли домен агрегатором
            for aggregator in self.aggregators:
                if aggregator in domain or domain in aggregator:
                    logger.info(f"Домен {domain} классифицирован как агрегатор")
                    self.domain_cache[domain] = 'other'
                    self.processed_domains.add(domain)
                    self.stats['others_found'] += 1
                    return 'other'
            
            # Если в заголовке есть признаки поставщика, классифицируем как поставщика
            if re.search(self.supplier_patterns, title, re.IGNORECASE):
                logger.info(f"Домен {domain} классифицирован как поставщик по заголовку")
                self.domain_cache[domain] = 'supplier'
                self.processed_domains.add(domain)
                self.stats['suppliers_found'] += 1
                return 'supplier'
            
            # Скачиваем и анализируем контент сайта
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=timeout, 
                                          headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Проверяем наличие признаков поставщика в HTML
                            if re.search(self.supplier_patterns, html, re.IGNORECASE):
                                logger.info(f"Домен {domain} классифицирован как поставщик по содержимому")
                                self.domain_cache[domain] = 'supplier'
                                self.processed_domains.add(domain)
                                self.stats['suppliers_found'] += 1
                                return 'supplier'
                            else:
                                logger.info(f"Домен {domain} классифицирован как другой тип сайта")
                                self.domain_cache[domain] = 'other'
                                self.processed_domains.add(domain)
                                self.stats['others_found'] += 1
                                return 'other'
                        else:
                            logger.warning(f"Не удалось получить содержимое {url}, статус: {response.status}")
                            # Если не удалось проанализировать, считаем "другим"
                            self.domain_cache[domain] = 'other'
                            self.processed_domains.add(domain)
                            self.stats['others_found'] += 1
                            return 'other'
            except Exception as e:
                logger.error(f"Ошибка при скачивании {url}: {str(e)}")
                # Если не удалось проанализировать, считаем "другим"
                self.domain_cache[domain] = 'other'
                self.processed_domains.add(domain)
                self.stats['others_found'] += 1
                return 'other'
                
        except Exception as e:
            logger.error(f"Ошибка при классификации {url}: {str(e)}")
            self.stats['errors'] += 1
            return None
    
    async def classify_batch(self, sites: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Классифицирует пакет сайтов и возвращает списки поставщиков и других сайтов.
        
        Args:
            sites: Список словарей с информацией о сайтах (обязательные ключи: url, title)
            
        Returns:
            Tuple[List[Dict], List[Dict]]: Списки поставщиков и других сайтов
        """
        suppliers = []
        others = []
        
        # Создаем задачи для асинхронного выполнения
        tasks = []
        for site in sites:
            url = site.get('url', '')
            title = site.get('title', '')
            
            # Пропускаем пустые URL
            if not url:
                continue
                
            # Получаем домен
            try:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                
                # Удаляем www. из домена, если есть
                if domain.startswith('www.'):
                    domain = domain[4:]
                    
                # Если домен уже обрабатывался, используем кэшированный результат
                if domain in self.processed_domains:
                    self.stats['already_processed'] += 1
                    if self.domain_cache.get(domain) == 'supplier':
                        suppliers.append(site)
                    else:
                        others.append(site)
                else:
                    # Добавляем задачу на классификацию
                    tasks.append(self.classify_site(url, title))
            except Exception as e:
                logger.error(f"Ошибка при обработке URL {url}: {str(e)}")
                others.append(site)
        
        # Выполняем все задачи параллельно
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Ошибка при классификации: {str(result)}")
                    others.append(sites[i])
                elif result == 'supplier':
                    suppliers.append(sites[i])
                else:
                    others.append(sites[i])
        
        self.stats['total_processed'] += len(sites)
        return suppliers, others
    
    def get_stats(self) -> Dict:
        """Возвращает статистику классификации."""
        return self.stats
    
    def clear_cache(self):
        """Очищает кэш доменов."""
        self.domain_cache.clear()
        self.processed_domains.clear()
        self.stats = {
            'total_processed': 0,
            'suppliers_found': 0,
            'others_found': 0,
            'already_processed': 0,
            'errors': 0
        } 