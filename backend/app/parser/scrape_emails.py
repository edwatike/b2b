import httpx
import re

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

async def scrape_emails_from_url(url: str) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            emails = list(set(EMAIL_REGEX.findall(resp.text)))
            return emails
    except Exception:
        return []
