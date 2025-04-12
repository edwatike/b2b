from fastapi import APIRouter, Query
from typing import List

router = APIRouter()

# Временно фейковые данные
@router.get("/search")
async def search_suppliers(query: str = Query(..., min_length=2)):
    suppliers = [
        {
            "name": "ООО ТрубаМеталл",
            "city": "Москва",
            "inn": "7712345678",
            "email": "info@trubametal.ru",
            "site": "https://trubametal.ru"
        },
        {
            "name": "ИП Стальные Решения",
            "city": "Санкт-Петербург",
            "inn": "7801234567",
            "email": "sales@stalres.ru",
            "site": "https://stalres.ru"
        }
    ]
    return {"query": query, "results": suppliers}
