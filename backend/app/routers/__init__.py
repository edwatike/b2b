from .companies import router as companies_router
from .search import router as search_router
from fastapi import APIRouter

router = APIRouter()
router.include_router(companies_router)
router.include_router(search_router)
