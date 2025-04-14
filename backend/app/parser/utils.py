import re
from urllib.parse import urlparse
from typing import Optional, List, Set
import logging
import random
import asyncio
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('parser.log')
    ]
)
logger = logging.getLogger(__name__)

def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception as e:
        logger.error(f"Error extracting domain from {url}: {e}")
        return ""

def clean_url(url: str) -> str:
    """Clean and normalize URL."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.rstrip('/')

def extract_emails(text: str, patterns: List[str]) -> Set[str]:
    """Extract email addresses from text using multiple patterns."""
    emails = set()
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        for email in found:
            if email.startswith('mailto:'):
                email = email[7:]
            emails.add(email.lower())
    return emails

def extract_phones(text: str, patterns: List[str]) -> Set[str]:
    """Extract phone numbers from text using multiple patterns."""
    phones = set()
    for pattern in patterns:
        found = re.findall(pattern, text)
        for phone in found:
            # Normalize phone number format
            clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
            if clean_phone.startswith('8'):
                clean_phone = '+7' + clean_phone[1:]
            phones.add(clean_phone)
    return phones

def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove special characters
    text = re.sub(r'[^\w\s@\-\+\(\)]', ' ', text)
    return text.strip()

async def random_delay(min_delay: float, max_delay: float):
    """Add random delay between requests."""
    delay = random.uniform(min_delay, max_delay)
    await asyncio.sleep(delay)

def get_random_user_agent(user_agents: List[str]) -> str:
    """Get random user agent from list."""
    return random.choice(user_agents)

def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False 