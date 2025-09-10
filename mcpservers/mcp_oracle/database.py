import oracledb
import structlog
from contextlib import contextmanager
from typing import Generator
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger(__name__)

class OracleSettings(BaseSettings):
    """Oracle database connection settings with security best practices."""
    
    model_config = SettingsConfigDict(
        env_file="/Users/kamleshpanchal/projects/quick-starts/ai-va/APPENG-3541-1/mcpservers/mcp_oracle/.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Oracle connection parameters
    oracle_user: str = Field(..., description="Oracle database username", alias="ORACLE_USER")
    oracle_password: str = Field(..., description="Oracle database password", alias="ORACLE_PASSWORD")
    oracle_host: str = Field(default="oracle23ai.an-oracle-23ai", description="Oracle database host", alias="ORACLE_HOST")
    oracle_port: int = Field(default=1521, description="Oracle database port", alias="ORACLE_PORT")
    oracle_service_name: str = Field(default="freepdb1", description="Oracle service name", alias="ORACLE_SERVICE_NAME")
    
    # Server configuration
    mcp_server_port: int = Field(default=8005, description="MCP server port", alias="MCP_SERVER_PORT")
    mcp_server_host: str = Field(default="0.0.0.0", description="MCP server host", alias="MCP_SERVER_HOST")
    
    # Security settings
    environment: str = Field(default="development", description="Environment: development/production", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", description="Logging level", alias="LOG_LEVEL")
    
    @property
    def oracle_dsn(self) -> str:
        """Construct Oracle DSN from components."""
        return f"{self.oracle_host}:{self.oracle_port}/{self.oracle_service_name}"
    
    def get_connection_config(self) -> dict:
        """Get sanitized connection config for logging."""
        return {
            "user": self.oracle_user,
            "host": self.oracle_host,
            "port": self.oracle_port,
            "service_name": self.oracle_service_name,
            "dsn": self.oracle_dsn
        }

# Global settings instance
settings = OracleSettings()

@contextmanager
def get_oracle_connection() -> Generator[oracledb.Connection, None, None]:
    """
    Get Oracle database connection context manager with security best practices.
    
    Features:
    - Automatic connection cleanup
    - Secure password handling (never logged)
    - Connection pooling ready
    - Transaction autocommit enabled
    """
    connection = None
    try:
        logger.info(
            "Establishing Oracle connection",
            connection_info=settings.get_connection_config()
        )
        
        connection = oracledb.connect(
            user=settings.oracle_user,
            password=settings.oracle_password,  # Never logged
            dsn=settings.oracle_dsn
        )
        connection.autocommit = True
        
        logger.debug("Oracle connection established successfully")
        yield connection
        
    except oracledb.Error as e:
        logger.error("Oracle connection failed", error=str(e), error_code=getattr(e, 'code', 'unknown'))
        raise
    except Exception as e:
        logger.error("Unexpected connection error", error=str(e))
        raise
    finally:
        if connection:
            try:
                connection.close()
                logger.debug("Oracle connection closed")
            except Exception as e:
                logger.warning("Error closing Oracle connection", error=str(e))

def test_connection() -> bool:
    """Test Oracle database connectivity for health checks."""
    try:
        with get_oracle_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM DUAL")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
    except Exception as e:
        logger.error("Connection test failed", error=str(e))
        return False