from app.schemas.query import SearchRequest, SearchResponse

async def search_suppliers(query: SearchRequest) -> SearchResponse:
    # TODO: заменить на реальный парсинг
    dummy_result = {
        "results": [
            {
                "company": "ООО МеталлПром",
                "website": "https://metallprom.ru",
                "email": "sales@metallprom.ru",
                "product_found": True
            }
        ]
    }
    return SearchResponse(**dummy_result)
