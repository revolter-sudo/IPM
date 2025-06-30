from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.app.schemas.constants import HOST_URL


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

# SQLAlchemy setup with optimized connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,  # Adjust based on server capacity
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True  # Verify connections before using them
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
