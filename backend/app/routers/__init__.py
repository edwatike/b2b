from fastapi import APIRouter
from . import companies, search, products  # добавляем products

router = APIRouter()
router.include_router(companies.router, prefix="/companies", tags=["companies"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(products.router, prefix="/products", tags=["products"])

