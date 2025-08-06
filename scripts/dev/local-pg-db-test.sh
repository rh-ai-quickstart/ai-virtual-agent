#!/bin/bash -e

# AI Virtual Agent: Database connectivity test using SQLAlchemy (same as application)

# Set default values for database connection
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-admin}
DB_NAME=${DB_NAME:-ai_virtual_agent}
DB_PASSWORD=${DB_PASSWORD:-password}

echo "🔍 Testing AI Virtual Agent database connectivity..."
echo "Database: ${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Test database connectivity using SQLAlchemy (exactly like the backend does)
python3 -c "
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_database_connection():
    # Use the same DATABASE_URL format as the backend
    DATABASE_URL = f'postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}'
    
    print(f'Testing connection: {DATABASE_URL}')
    
    try:
        # Create async engine like the backend does
        engine = create_async_engine(DATABASE_URL, echo=False)
        
        async with engine.begin() as conn:
            # Test basic connectivity
            result = await conn.execute(text('SELECT version();'))
            version = result.fetchone()[0]
            print(f'✅ Database connection successful!')
            print(f'   PostgreSQL version: {version[:50]}...')
            
            # Test basic database operations
            await conn.execute(text('CREATE TEMP TABLE test_table (id SERIAL)'))
            await conn.execute(text('DROP TABLE test_table'))
            print(f'✅ Database write permissions verified')
            
            # Test application-style UUID generation (Python uuid, not PostgreSQL extension)
            import uuid as py_uuid
            test_uuid = py_uuid.uuid4()
            print(f'✅ Python UUID generation works: {str(test_uuid)[:13]}...')
                
        await engine.dispose()
        print(f'\\n🎉 Database is ready for the AI Virtual Agent backend!')
        return True
        
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        print(f'\\n💡 Make sure PostgreSQL is running: docker-compose up -d')
        return False

# Run the test
success = asyncio.run(test_database_connection())
sys.exit(0 if success else 1)
"
