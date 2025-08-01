# Backend

FastAPI backend for the AI Virtual Agent Kickstart project. For complete setup instructions, see the [Contributing Guide](../CONTRIBUTING.md).

## Quick API Access

- **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Project Structure

```
backend/
├── main.py               # FastAPI app entrypoint, includes routers
├── database.py           # Database connection and session
├── models.py             # SQLAlchemy models
├── schemas.py            # Pydantic schemas
├── routes/               # API route modules
│   ├── users.py          # User management endpoints
│   ├── mcp_servers.py    # MCP server management
│   ├── knowledge_bases.py # Knowledge base operations
│   ├── virtual_assistants.py # Agent CRUD operations
│   ├── chat_sessions.py  # Chat session management
│   ├── tools.py          # Tool configuration endpoints
│   └── guardrails.py     # Guardrail management
├── utils/                # Utility modules
│   └── logging_config.py # Centralized logging setup
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables (not committed)
```

## Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - | `postgresql+asyncpg://user:pass@localhost:5432/dbname` |
| `LOCAL_DEV_ENV_MODE` | Bypass authentication for local development | `false` | `true` |

## Local Development Mode

When `LOCAL_DEV_ENV_MODE=true` is set, the application will:

- **Bypass OAuth authentication** - No need to set up OAuth proxy or authentication headers
- **Auto-create dev user** - Creates a default admin user (`dev-user` / `dev@localhost.dev`) in the database
- **Skip external auth services** - No calls to LlamaStack validation service
- **Maintain API compatibility** - All endpoints work the same way, just without auth requirements

**Security Note**: This feature is **disabled by default** (`LOCAL_DEV_ENV_MODE=false`). Only enable in local development environments.

### Usage

```bash
# Enable local dev mode
export LOCAL_DEV_ENV_MODE=true

# Or add to .env file
echo "LOCAL_DEV_ENV_MODE=true" >> .env

# Start the backend
python -m backend.main
```

## Developer Utilities (for advanced use cases only)

> **Note**: This section is provided for additional information and in most cases users won't need to execute these commands. These utilities are to be used only for advanced use cases. Standard development setup using `podman compose up` (see [Contributing Guide](../CONTRIBUTING.md)) handles all database setup automatically.

### Manual Database User Creation (PostgreSQL CLI)
*Only needed if setting up PostgreSQL manually instead of using Docker Compose:*
```sql
CREATE ROLE myuser WITH LOGIN PASSWORD 'mypassword';
GRANT ALL PRIVILEGES ON DATABASE ai_virtual_agent TO myuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO myuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO myuser;
```

### Password Hashing Reference (Python)
*For reference only - the application handles user creation automatically:*
```python
import bcrypt
password = b"mypassword"
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode())
```
