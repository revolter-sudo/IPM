import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI, Request
from fastapi_sqlalchemy import DBSessionMiddleware
import os
import uvicorn
import traceback
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # Add CORS import
from fastapi.templating import Jinja2Templates
from src.app.database.database import settings, SessionLocal
from src.app.services.auth_service import auth_router
from src.app.services.payment_service import payment_router
from src.app.services.project_service import project_router, balance_router
from src.app.services.khatabook_endpoints import khatabook_router
from src.app.services.inquiry_endpoints import inquiry_router
from src.app.services.attendance_endpoints import attendance_router
from src.app.services.attendance_service import auto_punch_out_users
from src.app.services.wage_endpoints import wage_router
from src.app.admin_panel.endpoints import admin_app
from src.app.sms_service.auth_service import sms_service_router
from src.app.services.machinery import machinery_router
from apscheduler.schedulers.background import BackgroundScheduler

from dotenv import load_dotenv
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

import redis
import time

# Import centralized logging configuration
from src.app.utils.logging_config import setup_logging, log_startup_info, get_logger, get_api_logger

# Initialize logging before any other operations
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "/app/logs"),
    app_name="ipm"
)

# Log startup information
log_startup_info()

# Get loggers
logger = get_logger(__name__)
api_logger = get_api_logger()

logger.info("************************************")
logger.info("IPM FastAPI Application Starting")
logger.info("************************************")


load_dotenv()
UPLOADS_DIR = os.getenv("UPLOADS_DIR")
SERVICE_FILE = os.getenv("SERVICE_FILE")

# Templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# FastAPI App
app = FastAPI()

# Configure CORS - Allow specific origins including Netlify domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins as a fallback
        "https://ipm-development.netlify.app",  # Explicitly allow the Netlify domain
        "https://dev.inqilabgroup.com",
        "https://inqilab.vercel.app/",
        "http://localhost:3000",  # For local development
        "http://localhost:8000",  # For local development
    ],
    allow_origin_regex="https://.*\.netlify\.app",  # Allow all Netlify subdomains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # Explicitly list all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to the browser
    max_age=86400,  # Cache preflight requests for 24 hours (in seconds)
)

app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)

from apscheduler.triggers.cron import CronTrigger
import logging
from pytz import timezone

scheduler = BackgroundScheduler()

def run_auto_punch_out():
    logger = logging.getLogger(__name__)
    logger.info("Triggered scheduled job: auto punch-out")

    db = SessionLocal()
    try:
        count = auto_punch_out_users(db)
        logger.info(f"Auto punch-out job completed. Users processed: {count}")
    except Exception as e:
        logger.error(f"Error during auto punch-out job: {str(e)}")
        logger.debug(traceback.format_exc())
    finally:
        db.close()
        logger.info("DB session closed after punch-out job")

# ✅ Run every 10 minutes in IST
# scheduler.add_job(
#     run_auto_punch_out,
#     CronTrigger(minute="*/10", timezone=timezone("Asia/Kolkata")),
#     id="auto_punch_out_job"
# )

scheduler.add_job(
    run_auto_punch_out,
    CronTrigger(hour=19, minute=30, timezone=timezone("Asia/Kolkata")),
    id="auto_punch_out_job"
)

# 🟩 PRODUCTION MODE: Uncomment this later when you're ready for daily at 7:30 PM
# scheduler.add_job(run_auto_punch_out, CronTrigger(hour=19, minute=30), id="auto_punch_out_job")

scheduler.start()

@app.on_event("startup")
def on_startup():
    logging.getLogger(__name__).info("FastAPI app started with scheduler running...")

# Performance middleware to track request timing and log API requests
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()

    # Log incoming request
    api_logger.info(f"Request: {request.method} {request.url.path} - Client: {request.client.host if request.client else 'unknown'}")

    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Log response with timing
    api_logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")

    # Log slow requests as warnings
    if process_time > 1.0:  # Log requests taking more than 1 second
        logger.warning(f"Slow request detected: {request.method} {request.url.path} took {process_time:.4f}s")

    return response

# Local
# os.makedirs("uploads", exist_ok=True)

# Mount the uploads folder for static access
# app.mount("/uploads", StaticFiles(directory="src/app/uploads"), name="uploads")

# Make sure /app/uploads exists in the container
os.makedirs(UPLOADS_DIR, exist_ok=True)

# scheduler = BackgroundScheduler()

# def run_auto_punch_out():
#     logger.info("Triggered scheduled job: auto punch-out")
#     db = SessionLocal()
#     try:
#         count = auto_punch_out_users(db)
#         logger.info(f"Auto punch-out job completed. Users processed: {count}")
#     except Exception as e:
#         logger.error(f"Error during auto punch-out job: {str(e)}")
#         logger.debug(traceback.format_exc())
#     finally:
#         db.close()
#         logger.info("DB session closed after punch-out job")

# # Schedule: every day at 7:30 PM IST (assuming local timezone or tz-aware setup)
# scheduler.add_job(run_auto_punch_out, 'cron', minute=10)
# logger.info("Auto punch-out job scheduled for daily execution at 7:30 PM IST")
# scheduler.start()
# logger.info("APScheduler started and running in background")

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
app.include_router(inquiry_router)
app.include_router(attendance_router)
app.include_router(wage_router)
app.include_router(sms_service_router)
app.include_router(machinery_router)
app.mount(path='/admin', app=admin_app)


SERVICE_ACCOUNT_PATH = SERVICE_FILE # noqa


if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)
    logger.info("--------------------------------")
    logger.info(f"Firebase Service Account Path: {SERVICE_ACCOUNT_PATH}")
    logger.info("Firebase Admin SDK Initialized Successfully")
    logger.info("--------------------------------")


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
        logger.info(f"Redis cache initialized successfully - Host: {redis_host}:{redis_port}")
    except Exception as e:
        # Fallback to in-memory cache if Redis is not available
        logger.warning(f"Redis connection failed: {str(e)}. Using in-memory cache.")
        try:
            from fastapi_cache.backends.memory import InMemoryBackend
            FastAPICache.init(InMemoryBackend(), prefix="ipm-cache")
            logger.info("In-memory cache initialized as fallback")
        except ImportError:
            logger.error("Failed to initialize fallback cache. Cache will be disabled.")


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
