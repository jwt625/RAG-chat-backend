from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .api import rag

settings = get_settings()

app = FastAPI(
    title="Blog Chatbot API",
    description="API for Jekyll blog chatbot with RAG capabilities",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rag.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Blog Chatbot API"} 