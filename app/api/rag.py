from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from ..rag.ingestion import ContentIngester

router = APIRouter(prefix="/rag", tags=["rag"])
ingester = ContentIngester()

class SearchQuery(BaseModel):
    query: str
    limit: int = 5

class SearchResult(BaseModel):
    content: str
    metadata: dict
    distance: float

class UpdateRequest(BaseModel):
    most_recent_only: bool = False

@router.post("/update")
async def update_content(request: UpdateRequest = UpdateRequest()):
    """Update blog content in ChromaDB
    
    Args:
        request: UpdateRequest with options:
            - most_recent_only: If True, only fetch and process the most recent post
    """
    result = await ingester.update_content(most_recent_only=request.most_recent_only)
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