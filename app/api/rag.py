from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from ..rag.ingestion import ContentIngester
from ..config import get_settings
from ..database import get_db
from ..security import limiter, get_current_user
from ..models import Chat, Message, User
from ..middleware.comprehensive_logger import log_rag_request
import httpx
import logging
import time
from sqlalchemy.orm import Session

router = APIRouter(prefix="/rag", tags=["rag"])
ingester = ContentIngester()
settings = get_settings()

class SearchQuery(BaseModel):
    query: str
    limit: int = 5

class SearchResult(BaseModel):
    content: str
    metadata: dict
    distance: float

class UpdateRequest(BaseModel):
    most_recent_only: bool = False
    num_posts: int | None = None  # If set, process this many most recent posts. If None, process all posts.

class GenerateQuery(BaseModel):
    query: str
    context_limit: int = 3  # Number of relevant chunks to use as context
    chat_id: Optional[int] = None  # Chat session ID
    message_history: Optional[List[Dict[str, str]]] = None  # Previous messages in the chat

class GenerateResponse(BaseModel):
    answer: str
    context_used: List[SearchResult]

class ProgressResponse(BaseModel):
    stage: str
    current: int
    total: int
    message: str

@router.post("/update")
@limiter.limit("1/hour")  # Rate limit content updates
async def update_content(
    request: Request,
    update_request: UpdateRequest = UpdateRequest(),
    current_user: dict = Depends(get_current_user)
):
    """Update blog content in ChromaDB

    Args:
        update_request: UpdateRequest with options:
            - most_recent_only: If True, only fetch and process the most recent post
            - num_posts: If set, process this many most recent posts. Ignored if most_recent_only is True.
    """
    result = await ingester.update_content(
        most_recent_only=update_request.most_recent_only,
        num_posts=update_request.num_posts
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.get("/status")
@limiter.limit("30/minute")  # Rate limit status checks
async def get_status(request: Request):
    """Get RAG system status"""
    try:
        collection = ingester.collection
        return {
            "status": "ok",
            "document_count": collection.count(),
            "name": collection.name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _internal_search(query: SearchQuery) -> List[SearchResult]:
    """Internal search function without auth"""
    try:
        results = ingester.collection.query(
            query_texts=[query.query],
            n_results=query.limit,
            include=["documents", "metadatas", "distances"]
        )
        
        return [
            SearchResult(
                content=doc,
                metadata=meta,
                distance=float(dist)
            )
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=List[SearchResult])
@limiter.limit("20/minute")  # Rate limit searches
async def search_content(
    request: Request,
    query: SearchQuery,
    current_user: dict = Depends(get_current_user)
):
    """Search blog content"""
    return await _internal_search(query)

@router.post("/generate", response_model=GenerateResponse)
@limiter.limit("10/minute")  # Rate limit
async def generate_response(
    request: Request,
    query: GenerateQuery,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate a response using RAG with DeepSeek LLM"""
    start_time = time.time()
    search_results = []
    generated_text = ""
    chat_id = None

    try:
        # Store user ID in request state for logging
        request.state.user_id = current_user["id"]
        # 1. Get or create chat session
        chat = None
        if query.chat_id:
            chat = db.query(Chat).filter(
                Chat.id == query.chat_id,
                Chat.user_id == current_user["id"]
            ).first()
            if not chat:
                raise HTTPException(status_code=404, detail="Chat session not found")
        else:
            chat = Chat(
                user_id=current_user["id"],
                title=query.query[:50] + "..."  # Use first 50 chars as title
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)

        # 2. Get relevant context using search
        search_results = await _internal_search(SearchQuery(query=query.query, limit=query.context_limit))
        
        # 3. Format context and query for DeepSeek
        context_text = "\n\n".join([
            f"Context {i+1} (Source: {result.metadata.get('title', 'Unknown')}, Date: {result.metadata.get('date', 'Unknown')}):\n{result.content}"
            for i, result in enumerate(search_results)
        ])
        
        # 4. Build conversation history
        conversation_history = []
        if query.message_history:
            conversation_history.extend(query.message_history[-5:])  # Use last 5 messages
        
        prompt = f"""You are an AI research assistant helping users find and summarize information from a blog that covers various technical topics including quantum computing, machine learning, software development, and more.

Your task is to:
1. Analyze the provided context from different blog posts
2. Extract relevant information that answers the user's question
3. Provide a clear, well-structured response
4. Always cite your sources using the format [Title (Date)]
5. If the context doesn't contain enough information to fully answer the question, acknowledge this and only discuss what's available in the provided context

Previous conversation:
{format_conversation_history(conversation_history)}

Here is the relevant context from the blog:

{context_text}

Question: {query.query}

Answer (remember to cite sources):"""

        # 5. Call DeepSeek API
        if not settings.DEEPSEEK_API_KEY:
            raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY.get_secret_value()}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 8000
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"DeepSeek API error: {response.text}"
                )
                
            llm_response = response.json()
            generated_text = llm_response["choices"][0]["message"]["content"]
            
            # 6. Save messages to database
            user_message = Message(
                chat_id=chat.id,
                role="user",
                content=query.query
            )
            assistant_message = Message(
                chat_id=chat.id,
                role="assistant",
                content=generated_text,
                context_used=[{
                    "content": result.content[:10000],
                    "metadata": result.metadata,
                    "distance": result.distance
                } for result in search_results]
            )
            db.add(user_message)
            db.add(assistant_message)
            db.commit()

            # Enhanced logging for generate endpoint
            response_time_ms = (time.time() - start_time) * 1000
            response = GenerateResponse(
                answer=generated_text,
                context_used=search_results
            )

            # Log the RAG request with detailed information
            await log_rag_request(
                request=request,
                response=JSONResponse(content=response.dict()),
                response_time_ms=response_time_ms,
                query_data=query.dict(),
                context_used=[{
                    "content": result.content,
                    "metadata": result.metadata,
                    "distance": result.distance
                } for result in search_results],
                response_text=generated_text,
                chat_id=chat.id
            )

            return response
            
    except Exception as e:
        logging.error(f"Error in generate_response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Public health check endpoint"""
    return {"status": "healthy", "service": "RAG API"}

@router.post("/generate-test", response_model=GenerateResponse)
@limiter.limit("5/minute")  # Very restrictive rate limit for test endpoint
async def generate_response_test(
    request: Request,
    query: GenerateQuery
):
    """Generate a response using RAG with DeepSeek LLM (Test version without auth)"""
    start_time = time.time()
    search_results = []
    generated_text = ""

    try:
        # 1. Get relevant context using search
        search_results = await _internal_search(SearchQuery(query=query.query, limit=query.context_limit))
        
        # 2. Format context and query for DeepSeek
        context_text = "\n\n".join([
            f"Context {i+1} (Source: {result.metadata.get('title', 'Unknown')}, Date: {result.metadata.get('date', 'Unknown')}):\n{result.content}"
            for i, result in enumerate(search_results)
        ])
        
        prompt = f"""You are an AI research assistant helping users find and summarize information from a blog that covers various technical topics including quantum computing, machine learning, software development, and more.

Your task is to:
1. Analyze the provided context from different blog posts
2. Extract relevant information that answers the user's question
3. Provide a clear, well-structured response
4. Always cite your sources using the format [Title (Date)]
5. If the context doesn't contain enough information to fully answer the question, acknowledge this and only discuss what's available in the provided context

Here is the relevant context from the blog:

{context_text}

Question: {query.query}

Answer (remember to cite sources):"""

        # 3. Call DeepSeek API
        if not settings.DEEPSEEK_API_KEY:
            raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY.get_secret_value()}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 8000
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"DeepSeek API error: {response.text}"
                )
                
            llm_response = response.json()
            generated_text = llm_response["choices"][0]["message"]["content"]
            
            # Enhanced logging for generate-test endpoint
            response_time_ms = (time.time() - start_time) * 1000

            # Return with explicit CORS headers for mobile compatibility
            response_data = GenerateResponse(
                answer=generated_text,
                context_used=search_results
            )

            # Get origin from request
            origin = request.headers.get("origin", "*")
            if origin in settings.CORS_ORIGINS or "*" in settings.CORS_ORIGINS:
                allowed_origin = origin
            else:
                allowed_origin = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "*"

            json_response = JSONResponse(
                content=response_data.dict(),
                headers={
                    "Access-Control-Allow-Origin": allowed_origin,
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Accept",
                }
            )

            # Log the RAG request with detailed information (no chat_id for test endpoint)
            await log_rag_request(
                request=request,
                response=json_response,
                response_time_ms=response_time_ms,
                query_data=query.dict(),
                context_used=[{
                    "content": result.content,
                    "metadata": result.metadata,
                    "distance": result.distance
                } for result in search_results],
                response_text=generated_text,
                chat_id=None  # No chat session for test endpoint
            )

            return json_response
            
    except Exception as e:
        logging.error(f"Error in generate_response_test: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def format_conversation_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No previous conversation."
    
    formatted = []
    for msg in history:
        role = msg["role"].capitalize()
        content = msg["content"]
        formatted.append(f"{role}: {content}")
    
    return "\n\n".join(formatted)

@router.get("/progress", response_model=ProgressResponse)
async def get_progress():
    """Get current progress of content update"""
    return ingester.get_progress() 