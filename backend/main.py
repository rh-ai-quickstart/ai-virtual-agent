from fastapi import FastAPI, HTTPException
from .database import engine, Base, AsyncSessionLocal
from .routes import users, mcp_servers, knowledge_bases, virtual_assistants, chat_history, guardrails, model_servers, llama_stack
import logging
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import httpx
import sys

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()

origins = ["*"]  # Update this with the frontend domain in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        async with AsyncSessionLocal() as session:
            await mcp_servers.sync_mcp_servers(session)
    except Exception as e:
        print(f"Failed to sync MCP servers on startup: {str(e)}")
    
    async with AsyncSessionLocal() as session:
        try:
            await model_servers.sync_model_servers(session)
        except Exception as e:
            print(f"Failed to sync model servers on startup: {str(e)}")
    
    async with AsyncSessionLocal() as session:
        try:
            await knowledge_bases.sync_knowledge_bases(session)
        except Exception as e:
            print(f"Failed to sync knowledge bases on startup: {str(e)}")

app.include_router(users.router)
app.include_router(mcp_servers.router)
app.include_router(knowledge_bases.router)
app.include_router(virtual_assistants.router)
app.include_router(chat_history.router)
app.include_router(guardrails.router)
app.include_router(model_servers.router)
app.include_router(llama_stack.router)

# Serve React App (frontend)
class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        if len(sys.argv) > 1 and sys.argv[1] == "dev":
            # We are in Dev mode, proxy to the React dev server
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8000/{path}")
            return Response(response.text, status_code=response.status_code)
        else:
            try:
                return await super().get_response(path, scope)
            except (HTTPException, StarletteHTTPException) as ex:
                if ex.status_code == 404:
                    return await super().get_response("index.html", scope)
                else:
                    raise ex


app.mount("/", SPAStaticFiles(directory="backend/public", html=True), name="spa-static-files")
