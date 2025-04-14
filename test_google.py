from app.parser.search_google import GoogleSearch
from app.parser.playwright_runner import PlaywrightRunner
import asyncio

async def test():
    runner = PlaywrightRunner()
    await runner.initialize()
    google = GoogleSearch(runner)
    results = await google.search("шпунт ларсена", limit=2)
    print(results)
    await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(test()) 