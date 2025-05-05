import logging
import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI, Request
from fastapi_sqlalchemy import DBSessionMiddleware
import os
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # Add CORS import
from fastapi.templating import Jinja2Templates
from src.app.database.database import settings
from src.app.services.auth_service import auth_router
from src.app.services.payment_service import payment_router
from src.app.services.project_service import project_router, balance_router
from src.app.services.khatabook_endpoints import khatabook_router
from src.app.admin_panel.endpoints import admin_app
from dotenv import load_dotenv
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
import redis
import time
logging.basicConfig(level=logging.INFO)
logging.info("************************************")
logging.info("Test log from main.py startup")
logging.info("************************************")


load_dotenv()
UPLOADS_DIR = os.getenv("UPLOADS_DIR")
SERVICE_FILE = os.getenv("SERVICE_FILE")

# Templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# FastAPI App
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)

# Performance middleware to track request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Local
# os.makedirs("uploads", exist_ok=True)

# Mount the uploads folder for static access
# app.mount("/uploads", StaticFiles(directory="src/app/uploads"), name="uploads")

# Make sure /app/uploads exists in the container
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Mount /uploads so that all subdirectories
# (including /payments) are accessible
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Mount static files directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(payment_router)
app.include_router(khatabook_router)
app.include_router(balance_router)
app.mount(path='/admin', app=admin_app)

SERVICE_ACCOUNT_PATH = SERVICE_FILE # noqa


if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
    logging.info("--------------------------------")
    logging.info(f"File Path: {SERVICE_ACCOUNT_PATH}")
    logging.info("FireBase Started")
    logging.info("--------------------------------")


# Initialize Redis cache on startup
@app.on_event("startup")
async def startup_event():
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_instance = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        FastAPICache.init(RedisBackend(redis_instance), prefix="ipm-cache")
        logging.info("Redis cache initialized successfully")
    except Exception as e:
        # Fallback to in-memory cache if Redis is not available
        logging.warning(f"Redis connection failed: {str(e)}. Using in-memory cache.")
        from fastapi_cache.backends.memory import InMemoryBackend
        FastAPICache.init(InMemoryBackend(), prefix="ipm-cache")


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/docs")

@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}


@app.get("/performance")
def performance_stats():
    """Return performance statistics for monitoring."""
    from src.app.middleware.performance import get_query_stats

    # Get database query statistics
    query_stats = get_query_stats()

    return {
        "query_stats": query_stats,
        "cache_status": "active"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
