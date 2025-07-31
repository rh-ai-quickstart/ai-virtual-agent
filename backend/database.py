"""
Database configuration and session management
for the AI Virtual Agent Kickstart application.

This module sets up SQLAlchemy with async PostgreSQL support,
configures the database connection, and provides utilities
for managing database sessions and transactions.
"""

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """
    Dependency function that provides database sessions for FastAPI endpoints.

    Yields:
        AsyncSession: Database session that automatically handles cleanup
    """
    async with AsyncSessionLocal() as session:
        yield session
