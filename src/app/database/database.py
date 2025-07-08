from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.app.schemas.constants import HOST_URL
from src.app.utils.logging_config import get_database_logger, get_performance_logger
import time


# Configuration
class Settings(BaseSettings):
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_HOST: str 
    DB_PORT: int = 5432
    DB_NAME: str
    UPLOADS_DIR: str
    SERVICE_FILE: str
    REDIS_HOST: str
    REDIS_PORT: str
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_VERIFY_SERVICE_SID: str
    HOST_URL: str
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "/app/logs"


    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"


settings = Settings()

# Initialize loggers
db_logger = get_database_logger()
perf_logger = get_performance_logger()

# SQLAlchemy setup with optimized connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,  # Adjust based on server capacity
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True  # Verify connections before using them
)

# Add database event listeners for logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log database connections."""
    db_logger.info("Database connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout from pool."""
    db_logger.debug("Database connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin to pool."""
    db_logger.debug("Database connection checked in to pool")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Log database initialization
db_logger.info("Database engine and session factory initialized")
db_logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")

# DB Dependency with logging
def get_db():
    db = SessionLocal()
    db_logger.debug("Database session created")
    try:
        yield db
        db_logger.debug("Database session yielded successfully")
    except Exception as e:
        db_logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()
        db_logger.debug("Database session closed")
