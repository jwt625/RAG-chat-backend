import httpx
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from .text_processing import TextProcessor
from ..config import get_settings
import json

settings = get_settings()

class ContentIngester:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(allow_reset=True)
        )
        # Create or get the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="blog_content",
            metadata={"description": "Blog content embeddings"}
        )
        self.text_processor = TextProcessor()

    async def fetch_content_from_github(self, repo_owner: str = "jwt625", repo_name: str = "jwt625.github.io", branch: str = "master") -> List[Dict]:
        """Fetch content from GitHub repository"""
        async with httpx.AsyncClient() as client:
            # First get the list of files in _posts directory
            response = await client.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/_posts?ref={branch}",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            if response.status_code != 200:
                raise Exception(f"Failed to fetch repository contents: {response.text}")
            
            files = response.json()
            posts = []
            
            for file in files:
                if file["type"] == "file" and file["name"].endswith(".md"):
                    # Fetch raw content using raw.githubusercontent.com
                    raw_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/_posts/{file['name']}"
                    content_response = await client.get(raw_url)
                    if content_response.status_code == 200:
                        posts.append({
                            "id": file["sha"],
                            "name": file["name"],
                            "content": content_response.text,
                            "url": file["html_url"]
                        })
            return posts

    def process_and_store_content(self, posts: List[Dict]):
        """Process and store content in ChromaDB"""
        all_chunks = []
        
        # Process each post into chunks
        for post in posts:
            chunks = self.text_processor.process_post(post)
            all_chunks.extend(chunks)
        
        # Batch upsert all chunks
        if all_chunks:
            self.collection.upsert(
                ids=[chunk["id"] for chunk in all_chunks],
                documents=[chunk["content"] for chunk in all_chunks],
                metadatas=[{
                    **chunk["metadata"],
                    "url": chunk["metadata"].get("url", ""),
                    "post_name": str(chunk["metadata"].get("post_name", "")),
                    "chunk_index": str(chunk["metadata"].get("chunk_index", "")),
                    "total_chunks": str(chunk["metadata"].get("total_chunks", ""))
                } for chunk in all_chunks]
            )
        
        return len(all_chunks)

    async def update_content(self):
        """Update content in ChromaDB"""
        try:
            posts = await self.fetch_content_from_github()
            chunk_count = self.process_and_store_content(posts)
            return {
                "status": "success", 
                "message": f"Updated {len(posts)} posts with {chunk_count} chunks"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)} 