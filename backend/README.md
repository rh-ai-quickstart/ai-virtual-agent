# Backend Technical Reference

FastAPI backend for the AI Virtual Assistant project. For complete setup instructions, see the [Contributing Guide](../CONTRIBUTING.md).

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

## Developer Utilities

### Database User Creation (PostgreSQL CLI)
```sql
CREATE ROLE myuser WITH LOGIN PASSWORD 'mypassword';
GRANT ALL PRIVILEGES ON DATABASE ai_virtual_assistant TO myuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO myuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO myuser;
```

### Password Hashing (Python)
```python
import bcrypt
password = b"mypassword"
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode())
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost:5432/dbname` |
