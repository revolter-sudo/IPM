import os
import traceback
from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware
from src.app.database.database import settings
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    Form
)
from src.app.admin_panel.services import get_default_config_service
import logging
from src.app.admin_panel.schemas import AdminPanelResponse
logging.basicConfig(level=logging.INFO)

admin_app = FastAPI(
    title="Admin API",
    docs_url="/docs",          # docs within this sub-app will be at /admin/docs
    openapi_url="/openapi.json"
)

# If you need DB access in the admin sub-app, add DBSessionMiddleware again:
admin_app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)


# @admin_app.post(
#     "/default-config",
#     tags=['Default Config'],
#     status_code=201
# )
# def create_default_config

@admin_app.get(
    "/default-config",
    tags=['Default Config'],
    status_code=200,
)
def get_default_config():
    try:
        default_config = get_default_config_service()
        return AdminPanelResponse(
            data=default_config,
            message="Default Config Fetched Successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in get_default_config API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            message="Error in get_default_config API",
            status_code=500
        ).model_dump()
