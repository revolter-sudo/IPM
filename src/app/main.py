from fastapi import FastAPI
from fastapi_sqlalchemy import DBSessionMiddleware

from src.app.database.database import settings
from src.app.services.auth_service import auth_router
from src.app.services.payment_service import payment_router
from src.app.services.project_service import project_router

# FastAPI App
app = FastAPI()
app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(payment_router)


@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}
