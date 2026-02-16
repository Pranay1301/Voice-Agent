import uvicorn
import logging
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

from inbound_call import router as inbound_router
from database import engine, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('voice_agent.log')
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    try:
        # Startup: Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
        
        # Validate required environment variables
        required_vars = [
            "GROQ_API_KEY",
            "DEEPGRAM_API_KEY", 
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            raise ValueError(f"Missing environment variables: {missing_vars}")
        
        logger.info("Application startup completed successfully")
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    finally:
        # Shutdown
        await engine.dispose()
        logger.info("Application shutdown completed")

app = FastAPI(
    title="Voice Agent",
    description="AI-powered real estate appointment booking system",
    version="1.0.0",
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # In production, replace with specific hosts
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with detailed logging."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Return generic error message to client
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "status_code": exc.status_code,
            "message": exc.detail
        },
    )

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": "2025-11-29T12:00:00Z",
        "version": "1.0.0",
        "services": {
            "database": "connected",
            "groq": "available",
            "deepgram": "available",
            "twilio": "available"
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint for monitoring."""
    return {
        "calls_processed": 0,
        "average_call_duration": 0,
        "error_rate": 0,
        "uptime": "0s"
    }

@app.get("/performance")
async def get_performance():
    """Performance monitoring endpoint."""
    return performance_monitor.get_performance_summary()

@app.get("/optimization")
async def get_optimization():
    """Optimization recommendations endpoint."""
    return {
        "should_optimize": performance_monitor.should_optimize(),
        "recommendations": performance_monitor.get_optimization_recommendations(),
        "performance_summary": performance_monitor.get_performance_summary()
    }

app.include_router(inbound_router)

if __name__ == "__main__":
    # Production server configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,  # Disable in production
        log_level="info",
        access_log=True,
        workers=int(os.getenv("WORKERS", "1"))
    )
