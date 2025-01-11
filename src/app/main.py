from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
from pydantic_settings import BaseSettings
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os


# Configuration
class Settings(BaseSettings):
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"


settings = Settings()

# SQLAlchemy setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI App
app = FastAPI()
app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)

@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


# Directory structure setup
os.makedirs("src/app/models", exist_ok=True)
os.makedirs("src/app/schemas", exist_ok=True)
os.makedirs("src/app/routes", exist_ok=True)
os.makedirs("src/app/services", exist_ok=True)
os.makedirs("src/app/database", exist_ok=True)
os.makedirs("src/app/utils", exist_ok=True)
os.makedirs("src/app/tests", exist_ok=True)

# Create __init__.py files
for path in [
    "src/app",
    "src/app/models",
    "src/app/schemas",
    "src/app/routes",
    "src/app/services",
    "src/app/database",
    "src/app/utils",
    "src/app/tests",
]:
    with open(os.path.join(path, "__init__.py"), "w") as f:
        f.write("# Auto-generated init file")

# Alembic Setup: Create initial migration
# 1. Install Alembic if not installed: pip install alembic
# 2. Initialize Alembic: alembic init alembic
# 3. Configure alembic.ini: Set sqlaclchemy.url to DATABASE_URL
# 4. Generate Migration for Base
# alembic revision --autogenerate -m "Initial migration"
