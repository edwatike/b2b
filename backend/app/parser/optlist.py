import httpx
from selectolax.parser import HTMLParser
from typing import List
from app.models.result import ResultItem
from app.parser.base import BaseParser

class OptListParser(BaseParser):
    async def parse(self, keyword: str) -> List[ResultItem]:
        url = f"https://example.com/search?q={keyword}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            html = HTMLParser(r.text)

        results = []
        for el in html.css("div.company-card"):
            name = el.css_first(".title").text() if el.css_first(".title") else "Без названия"
            email = el.css_first(".email").text() if el.css_first(".email") else "unknown@example.com"
            site = el.css_first("a").attributes.get("href", "")
            results.append(ResultItem(name=name, email=email, city="N/A", site=site))
        
        return results