import logging
from logging.handlers import RotatingFileHandler
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .security import limiter
from .config import get_settings

settings = get_settings()

def setup_logging():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10000000,  # 10MB
        backupCount=5
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logging.getLogger().addHandler(handler)

def init_monitoring():
    # Initialize Sentry for error tracking
    sentry_sdk.init(
        dsn="your-sentry-dsn",  # TODO: Add to settings
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

def create_production_app() -> FastAPI:
    app = FastAPI(
        title="Blog Chatbot API",
        description="Production API for Jekyll blog chatbot with RAG capabilities",
        version="1.0.0",
        docs_url=None,  # Disable docs in production
        redoc_url=None  # Disable redoc in production
    )
    
    # Add security middlewares
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["your-domain.com"]  # TODO: Add to settings
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    
    # Add compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request, exc):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"}
        )
    
    return app

def configure_production():
    setup_logging()
    init_monitoring()
    return create_production_app() 