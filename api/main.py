"""FastAPI application entry point."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
from typing import Any

from app.api.completions import router as completions_router
from app.core.config import settings
log_level = getattr(logging, settings.log_level.upper())
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Text Completion Service",
    description="Provider-agnostic text generation API",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(completions_router, prefix="/api", tags=["completions"])

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(
        "application.startup",
        extra={
            "port": settings.port,
            "default_model": settings.default_model,
            "title": app.title,
            "version": app.version
        }
    )

@app.on_event("shutdown") 
async def shutdown_event():
    """Log application shutdown."""
    logger.info("application.shutdown")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Any, exc: HTTPException):
    """Custom HTTP exception handler."""
    logger.warning(
        "http.exception",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "url": str(request.url) if hasattr(request, 'url') else None
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=settings.port, 
        reload=True
    )
