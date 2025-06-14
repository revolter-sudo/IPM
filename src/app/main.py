import logging
import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
import os
import uvicorn
from fastapi.staticfiles import StaticFiles
from src.app.database.database import settings
from src.app.services.auth_service import auth_router
from src.app.services.payment_service import payment_router
from src.app.services.project_service import project_router, balance_router
from src.app.services.khatabook_endpoints import khatabook_router
from src.app.admin_panel.endpoints import admin_app
from src.app.sms_service.auth_service import sms_service_router

from dotenv import load_dotenv
logging.basicConfig(level=logging.INFO)
logging.info("************************************")
logging.info("Test log from main.py startup")
logging.info("************************************")


load_dotenv()
UPLOADS_DIR = os.getenv("UPLOADS_DIR")
SERVICE_FILE = os.getenv("SERVICE_FILE")

# FastAPI App
app = FastAPI()
app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)
# Local
# os.makedirs("uploads", exist_ok=True)

# Mount the uploads folder for static access
# app.mount("/uploads", StaticFiles(directory="src/app/uploads"), name="uploads")

# ===============# Make sure /app/uploads exists in the container
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Mount /uploads so that all subdirectories
# (including /payments) are accessible
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(payment_router)
app.include_router(khatabook_router)
app.include_router(balance_router)
app.include_router(sms_service_router)
app.mount(path='/admin', app=admin_app)

SERVICE_ACCOUNT_PATH = SERVICE_FILE # noqa


if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
    logging.info("--------------------------------")
    logging.info(f"File Path: {SERVICE_ACCOUNT_PATH}")
    logging.info("FireBase Started")
    logging.info("--------------------------------")

SERVICE_ACCOUNT_PATH = SERVICE_FILE # noqa


if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
    logging.info("--------------------------------")
    logging.info(f"File Path: {SERVICE_ACCOUNT_PATH}")
    logging.info("FireBase Started")
    logging.info("--------------------------------")


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
