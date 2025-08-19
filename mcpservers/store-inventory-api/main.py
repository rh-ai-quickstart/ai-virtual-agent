from contextlib import asynccontextmanager
from typing import AsyncGenerator as TypingAsyncGenerator  # Renamed to avoid clash
from typing import List

# Local imports
import crud
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession  # Import AsyncSession for type hinting

import database
import models


@asynccontextmanager
async def lifespan(app: FastAPI) -> TypingAsyncGenerator[None, None]:
    # Code to run on startup
    print("INFO:     Store Inventory API startup.")

    # Initialize database tables
    await database.create_db_and_tables()
    yield

    # Code to run on shutdown (if any)
    print("INFO:     Store Inventory API shutdown.")


app = FastAPI(
    title="Store Inventory API",
    description="A REST API server to manage products and orders for store inventory.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "store-inventory-api"}


@app.get(
    "/products/",
    response_model=List[models.Product],
    summary="Get a list of all products",
    description="Retrieve a paginated list of all products in the inventory.",
)
async def read_products(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(database.get_db)
):
    products = await crud.get_products(db, skip=skip, limit=limit)
    return products


@app.post(
    "/products/",
    response_model=models.Product,
    summary="Add a new product",
    description="Create a new product in the inventory system.",
)
async def create_product(
    product: models.ProductCreate, db: AsyncSession = Depends(database.get_db)
):
    # Check if product already exists by name can be added here
    return await crud.add_product(db=db, product=product)


@app.get(
    "/products/id/{product_id}",
    response_model=models.Product,
    summary="Get product by its ID",
    description="Retrieve a specific product by its unique identifier.",
)
async def read_product_by_id(
    product_id: int, db: AsyncSession = Depends(database.get_db)
):
    db_product = await crud.get_product_by_id(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.get(
    "/products/name/{product_name}",
    response_model=models.Product,
    summary="Get product by its name",
    description="Retrieve a specific product by its name.",
)
async def read_product_by_name(
    product_name: str, db: AsyncSession = Depends(database.get_db)
):
    db_product = await crud.get_product_by_name(db, name=product_name)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.get(
    "/products/search/",
    response_model=List[models.Product],
    summary="Search for products by query string",
    description="Search products by name or description using a query string.",
)
async def search_products_endpoint(
    query: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(database.get_db),
):
    products = await crud.search_products(db, query=query, skip=skip, limit=limit)
    if not products:
        raise HTTPException(
            status_code=404, detail="No products found matching your query"
        )
    return products


@app.delete(
    "/products/{product_id}",
    response_model=models.Product,
    summary="Remove a product by its ID",
    description="Delete a product from the inventory system.",
)
async def delete_product(product_id: int, db: AsyncSession = Depends(database.get_db)):
    db_product = await crud.remove_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.post(
    "/orders/",
    response_model=models.Order,
    summary="Place an order for a product",
    description="Create an order for a product, which will reduce inventory.",
)
async def create_order(
    order_details: models.ProductOrderRequest,
    db: AsyncSession = Depends(database.get_db),
):
    try:
        created_order = await crud.order_product(db=db, order_details=order_details)
        return created_order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:  # Catch other potential errors from CRUD
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while placing the order.",
        )


# To run this app (for local development):
# uvicorn store_inventory.main:app --reload --port 8002
