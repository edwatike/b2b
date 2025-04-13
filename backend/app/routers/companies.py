from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db import async_session
from app.models.company import Company

router = APIRouter()

# Получаем сессию БД
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

# Добавление компании
@router.post("/companies")
async def add_company(company: Company, session: AsyncSession = Depends(get_session)):
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company
