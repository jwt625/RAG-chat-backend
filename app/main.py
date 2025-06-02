from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .config import get_settings
from .api import rag

settings = get_settings()

app = FastAPI(
    title="Blog Chatbot API",
    description="API for Jekyll blog chatbot with RAG capabilities",
    version="1.0.0",
    default_response_class=JSONResponse  # Ensure proper JSON response handling
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure response settings
app.state.max_response_size = 10 * 1024 * 1024  # 10MB max response size

# Include routers
app.include_router(rag.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Blog Chatbot API"} 