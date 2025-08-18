import os

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Database configuration - build from components to avoid long lines
DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")
DATABASE_HOST = os.getenv("DATABASE_HOST", "store-inventory-api-postgresql")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "store_inventory")

DATABASE_URL = (
    f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}"
    f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
)

engine = create_async_engine(DATABASE_URL, echo=False)  # echo=True for debugging SQL

# expire_on_commit=False will prevent attributes from being expired
# after commit, which is useful for async code.
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


# SQLAlchemy models
class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(Text, nullable=True)
    inventory = Column(Integer, default=0)
    price = Column(Numeric(10, 2), nullable=False, server_default="0.00")

    orders = relationship("OrderDB", back_populates="product")


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    customer_identifier = Column(String)

    product = relationship("ProductDB", back_populates="orders")


# Function to create tables (now async)
async def create_db_and_tables():
    async with engine.begin() as conn:
        # For production, use Alembic migrations instead of create_all
        await conn.run_sync(Base.metadata.create_all)
    print("INFO:     Store Inventory database tables checked/created.")


# Dependency to get DB session (now async)
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit if no exceptions were raised
        except Exception:
            await session.rollback()  # Rollback on error
            raise
        finally:
            await session.close()  # Good practice
