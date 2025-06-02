from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from ..rag.ingestion import ContentIngester
from ..config import get_settings
import httpx

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

class GenerateResponse(BaseModel):
    answer: str
    context_used: List[SearchResult]

class ProgressResponse(BaseModel):
    stage: str
    current: int
    total: int
    message: str

@router.post("/update")
async def update_content(request: UpdateRequest = UpdateRequest()):
    """Update blog content in ChromaDB
    
    Args:
        request: UpdateRequest with options:
            - most_recent_only: If True, only fetch and process the most recent post
            - num_posts: If set, process this many most recent posts. Ignored if most_recent_only is True.
    """
    result = await ingester.update_content(
        most_recent_only=request.most_recent_only,
        num_posts=request.num_posts
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.get("/status")
async def get_status():
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

@router.post("/search", response_model=List[SearchResult])
async def search_content(query: SearchQuery):
    """Search blog content"""
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

@router.post("/generate", response_model=GenerateResponse)
async def generate_response(query: GenerateQuery):
    """Generate a response using RAG with DeepSeek LLM"""
    try:
        # 1. Get relevant context using search
        search_results = await search_content(SearchQuery(query=query.query, limit=query.context_limit))
        
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
                "https://api.deepseek.com/chat/completions",
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
            
            # Create response with limited context to prevent large responses
            return GenerateResponse(
                answer=generated_text,
                context_used=[{
                    "content": result.content[:10000],  # Limit context size
                    "metadata": result.metadata,
                    "distance": result.distance
                } for result in search_results]
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress", response_model=ProgressResponse)
async def get_progress():
    """Get current progress of content update"""
    return ingester.get_progress() 