import httpx
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from .text_processing import TextProcessor
from ..config import get_settings

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

    async def fetch_content_from_github(self, repo_owner: str = "jwt625", repo_name: str = "jwt625.github.io") -> List[Dict]:
        """Fetch content from GitHub repository"""
        async with httpx.AsyncClient() as client:
            # Get repository contents
            response = await client.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/_posts",
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            if response.status_code != 200:
                raise Exception(f"Failed to fetch repository contents: {response.text}")
            
            posts = []
            for item in response.json():
                if item["type"] == "file" and item["name"].endswith(".md"):
                    # Fetch raw content
                    content_response = await client.get(item["download_url"])
                    if content_response.status_code == 200:
                        posts.append({
                            "id": item["sha"],
                            "name": item["name"],
                            "content": content_response.text
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
                metadatas=[chunk["metadata"] for chunk in all_chunks]
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