from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://b2b_user:b2b_pass@db:5432/b2b_db")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    import app.models  # чтобы SQLModel знал все модели
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
