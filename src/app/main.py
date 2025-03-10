from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
import os
from fastapi.staticfiles import StaticFiles
from src.app.database.database import settings
from src.app.services.auth_service import auth_router
from src.app.services.payment_service import payment_router
from src.app.services.project_service import project_router
from src.app.services.khatabook_endpoints import khatabook_router
from dotenv import load_dotenv

load_dotenv()
UPLOADS_DIR = os.getenv("UPLOADS_DIR")

# FastAPI App
app = FastAPI()
app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)
# Local
# os.makedirs("uploads", exist_ok=True)

# Mount the uploads folder for static access
# app.mount("/uploads", StaticFiles(directory="src/app/uploads"), name="uploads")

#===============# Make sure /app/uploads exists in the container
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Mount /uploads so that all subdirectories (including /payments) are accessible
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(payment_router)
app.include_router(khatabook_router)


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}
