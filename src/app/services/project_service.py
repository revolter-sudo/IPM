from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.app.database.database import get_db
from src.app.database.models import User
from src.app.schemas.auth_service_schamas import Token
from uuid import UUID
from sqlalchemy import and_

# Router Setup
project_router = APIRouter(prefix="/projects")

