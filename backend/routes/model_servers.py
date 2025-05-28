from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Dict, Any

from .. import models, schemas
from ..database import get_db
from ..api.llamastack import client
#TODO: fix name conflict models (list) and models (module)
from ..models import ModelServer

router = APIRouter(prefix="/model_servers", tags=["Model Servers"])

@router.post("/", response_model=schemas.ModelServerRead, status_code=status.HTTP_201_CREATED)
async def create_model_server(server: schemas.ModelServerCreate, db: AsyncSession = Depends(get_db)):
    model_server = models.ModelServer(**server.dict())
    db.add(model_server)
    await db.commit()
    await db.refresh(model_server)
    return model_server

@router.get("/", response_model=List[schemas.ModelServerRead])
async def read_model_servers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ModelServer))
    return result.scalars().all()

@router.get("/{server_id}", response_model=schemas.ModelServerRead)
async def read_model_server(server_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ModelServer).where(models.ModelServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server

@router.put("/{server_id}", response_model=schemas.ModelServerRead)
async def update_mcp_server(server_id: UUID, server: schemas.ModelServerCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ModelServer).where(models.ModelServer.id == server_id))
    db_server = result.scalar_one_or_none()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")
    for field, value in server.dict().items():
        setattr(db_server, field, value)
    await db.commit()
    await db.refresh(db_server)
    return db_server

@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_server(server_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ModelServer).where(models.ModelServer.id == server_id))
    db_server = result.scalar_one_or_none()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")
    await db.delete(db_server)
    await db.commit()
    return None

async def sync_model_servers(db: AsyncSession):
    try:
        print("Starting model server sync")
        print("Fetching models from LlamaStack")
        try:
            response = client.models.list()
            
            if isinstance(response, list):
                models = [item.__dict__ for item in response]
            elif isinstance(response, dict):
                models = response.get("data", [])
            elif hasattr(response, "data"):
                models = response.data
            else:
                print(f"Unexpected response type: {type(response)}")
                models = []
                
            
        except Exception as e:
            raise Exception(f"Failed to fetch models from LlamaStack: {str(e)}")
    
        print("Fetching existing model servers from database...")
        result = await db.execute(select(ModelServer))
        existing_servers = {server.name: server for server in result.scalars().all()}
        print(f"Found {len(existing_servers)} existing model servers: {list(existing_servers.keys())}")
        
        synced_servers = []
        
        print("Processing models...")
        for model in models:
            try:
                if not model.get("name"):
                    print(f"Skipping model without name: {model}")
                    continue
                    
                server_data = {
                    "name": model["name"],
                    "title": model.get("title", model["name"]),
                    "description": model.get("description", ""),
                    "endpoint_url": model.get("endpoint_url", ""),
                    "configuration": model.get("configuration", {}),
                    "created_by": "admin"
                }
                print(f"Processing model {model['name']} with data: {server_data}")
                
                if model["name"] in existing_servers:
                    print(f"Updating existing model server: {model['name']}")
                    server = existing_servers[model["name"]]
                    for field, value in server_data.items():
                        setattr(server, field, value)
                else:
                    print(f"Creating new model server: {model['name']}")
                    server = models.ModelServer(**server_data)
                    db.add(server)
                
                synced_servers.append(server)
            except Exception as e:
                print(f"Error processing model {model.get('name', 'unknown')}: {str(e)}")
                continue
        
        print("Checking for model servers to remove...")
        for server_name, server in existing_servers.items():
            if not any(m.get("name") == server_name for m in models):
                print(f"Removing model server that no longer exists: {server_name}")
                await db.delete(server)
        
        print("Committing changes to database...")
        await db.commit()
        
        print("Refreshing synced model servers...")
        for server in synced_servers:
            await db.refresh(server)
        
        print(f"Sync complete. Synced {len(synced_servers)} model servers.")
        return synced_servers
        
    except Exception as e:
        print(f"Error during sync: {str(e)}")
        raise Exception(f"Failed to sync model servers: {str(e)}")

@router.post("/sync", response_model=List[schemas.ModelServerRead])
async def sync_model_servers_endpoint(db: AsyncSession = Depends(get_db)):
    try:
        return await sync_model_servers(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
