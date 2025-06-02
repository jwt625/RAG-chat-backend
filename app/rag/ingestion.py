import httpx
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from .text_processing import TextProcessor
from ..config import get_settings
import json
import logging
from datetime import datetime
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

class ContentIngester:
    def __init__(self):
        logger.info("Initializing ContentIngester")
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
            settings=Settings(allow_reset=True)
        )
        # Create or get the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="blog_content",
            metadata={"description": "Blog content embeddings"}
        )
        logger.info(f"Connected to ChromaDB collection: {self.collection.name}")
        self.text_processor = TextProcessor()

    def _is_post_file(self, filename: str) -> bool:
        """Check if a file is a blog post based on its name pattern (YYYY-MM-DD-*)"""
        pattern = r'^\d{4}-\d{2}-\d{2}-.*\.md$'
        return bool(re.match(pattern, filename))

    async def fetch_markdown_content(self, repo_owner: str = "jwt625", repo_name: str = "jwt625.github.io", most_recent_only: bool = False) -> List[Dict]:
        """Fetch markdown files from _posts directory"""
        async with httpx.AsyncClient() as client:
            # Get list of markdown files
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/_posts"
            logger.info(f"Fetching files from: {api_url}")
            
            response = await client.get(
                api_url,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            response.raise_for_status()
            
            # Filter for post files only (YYYY-MM-DD-*.md)
            files = [f for f in response.json() if f["type"] == "file" and self._is_post_file(f["name"])]
            logger.info(f"Found {len(files)} blog posts")
            logger.debug(f"Posts: {[f['name'] for f in files]}")

            if most_recent_only:
                # Sort files by date in filename (YYYY-MM-DD-*)
                files.sort(key=lambda x: x["name"].split("-")[:3], reverse=True)
                files = files[:1]  # Keep only the most recent
                logger.info(f"Selected most recent post: {files[0]['name']}")
                logger.debug(f"Most recent post details: {files[0]}")
            
            # Download content for each file
            posts = []
            for file in files:
                raw_url = file["download_url"]
                logger.info(f"Downloading: {file['name']} from {raw_url}")
                
                content_response = await client.get(raw_url)
                content_response.raise_for_status()
                
                post = {
                    "id": file["sha"],
                    "name": file["name"],
                    "content": content_response.text,
                    "url": file["html_url"]
                }
                logger.debug(f"Downloaded post: {post['name']}")
                logger.debug(f"Content preview:\n{post['content'][:500]}...")
                posts.append(post)
            
            return posts

    def process_and_store_content(self, posts: List[Dict]) -> int:
        """Process and store content in ChromaDB"""
        logger.info(f"Processing {len(posts)} posts")
        all_chunks = []
        
        # Process each post into chunks
        for post in posts:
            logger.info(f"Processing post: {post['name']}")
            chunks = self.text_processor.process_post(post)
            logger.info(f"Generated {len(chunks)} chunks for post: {post['name']}")
            logger.debug(f"First chunk preview:\n{chunks[0]['content'][:200] if chunks else 'No chunks generated'}")
            all_chunks.extend(chunks)
        
        # Batch upsert all chunks
        if all_chunks:
            logger.info(f"Upserting {len(all_chunks)} chunks to ChromaDB")
            try:
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
                logger.info("Successfully stored chunks in ChromaDB")
            except Exception as e:
                logger.error(f"Failed to store chunks in ChromaDB: {str(e)}")
                raise
        
        return len(all_chunks)

    async def update_content(self, most_recent_only: bool = False) -> Dict:
        """Update content in ChromaDB"""
        try:
            logger.info("Starting content update")
            posts = await self.fetch_markdown_content(most_recent_only=most_recent_only)
            chunk_count = self.process_and_store_content(posts)
            result = {
                "status": "success", 
                "message": f"Updated {len(posts)} posts with {chunk_count} chunks"
            }
            logger.info(result["message"])
            return result
        except Exception as e:
            error_msg = f"Error during content update: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg} 