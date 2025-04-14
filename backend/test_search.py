#!/usr/bin/env python3
import asyncio
from app.parser.search_google import GoogleSearch
from app.parser.playwright_runner import PlaywrightRunner

async def test_google_search():
    """Тестирует функциональность поиска в Google"""
    print("Инициализация PlaywrightRunner...")
    runner = PlaywrightRunner()
    await runner.initialize()
    
    try:
        print("Инициализация GoogleSearch...")
        google = GoogleSearch(runner)
        
        print("Выполнение поиска 'шпунт ларсена'...")
        results = await google.search('шпунт ларсена', limit=5)
        
        print(f"\nНайдено {len(results)} результатов:\n")
        for r in results:
            print(f"{r.position}. {r.title}")
            print(f"   URL: {r.url}")
            print(f"   Сниппет: {r.snippet[:100]}...\n")
            
    finally:
        print("Очистка ресурсов...")
        await runner.cleanup()
        print("Тест завершен.")

if __name__ == "__main__":
    asyncio.run(test_google_search()) 