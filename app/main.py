from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from .config import get_settings
from .api import rag, auth
from .middleware.comprehensive_logger import comprehensive_logger
import logging
import time
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

settings = get_settings()

app = FastAPI(
    title="Blog Chatbot API",
    description="API for Jekyll blog chatbot with RAG capabilities",
    version="1.0.0",
    default_response_class=JSONResponse  # Ensure proper JSON response handling
)

# Configure CORS with mobile-friendly settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,  # Set to False for better mobile compatibility
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Configure response settings
app.state.max_response_size = 10 * 1024 * 1024  # 10MB max response size

# Comprehensive request logging middleware
@app.middleware("http")
async def comprehensive_logging_middleware(request: Request, call_next):
    # Record start time
    start_time = time.time()

    # Skip rate limiting for OPTIONS requests
    if request.method == "OPTIONS":
        request.state.view_rate_limit = None

    # Process request
    response = await call_next(request)

    # Calculate response time
    response_time_ms = (time.time() - start_time) * 1000

    # Log the request comprehensively
    await comprehensive_logger.log_request(request, response, response_time_ms)

    # Keep basic console logging for debugging
    logger.info(f"Request: {request.method} {request.url.path} - {response.status_code} - {response_time_ms:.2f}ms")

    return response

# Explicit OPTIONS handler for mobile browser preflight requests
@app.options("/rag/generate-test")
async def preflight_handler_generate_test(request: Request):
    """Handle CORS preflight requests for mobile browsers"""
    origin = request.headers.get("origin", "*")
    
    # Check if origin is allowed
    if origin in settings.CORS_ORIGINS or "*" in settings.CORS_ORIGINS:
        allowed_origin = origin
    else:
        # Default to first allowed origin if specific origin not in list
        allowed_origin = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "*"
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
            "Access-Control-Max-Age": "86400",
        }
    )

# Generic OPTIONS handler for all RAG endpoints
@app.options("/rag/{full_path:path}")
async def preflight_handler_rag(request: Request):
    """Handle CORS preflight requests for all RAG endpoints"""
    origin = request.headers.get("origin", "*")
    
    # Check if origin is allowed
    if origin in settings.CORS_ORIGINS or "*" in settings.CORS_ORIGINS:
        allowed_origin = origin
    else:
        # Default to first allowed origin if specific origin not in list
        allowed_origin = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "*"
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept, Authorization",
            "Access-Control-Max-Age": "86400",
        }
    )

# Include routers
app.include_router(auth.router)
app.include_router(rag.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Blog Chatbot API"} 