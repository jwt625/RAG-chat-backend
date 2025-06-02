import httpx
from typing import List, Dict, Set
import chromadb
from chromadb.config import Settings
from .text_processing import TextProcessor
from ..config import get_settings
import json
import logging
from datetime import datetime
import re
from tqdm import tqdm
import asyncio

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
        self._progress = {"stage": "", "current": 0, "total": 0, "message": ""}

    def update_progress(self, stage: str, current: int, total: int, message: str = ""):
        """Update progress tracking"""
        self._progress = {
            "stage": stage,
            "current": current,
            "total": total,
            "message": message
        }
        logger.info(f"Progress - {stage}: {current}/{total} {message}")

    def get_progress(self) -> Dict:
        """Get current progress"""
        return self._progress

    def _is_post_file(self, filename: str) -> bool:
        """Check if a file is a blog post based on its name pattern (YYYY-MM-DD-*)"""
        pattern = r'^\d{4}-\d{2}-\d{2}-.*\.md$'
        return bool(re.match(pattern, filename))

    async def fetch_markdown_content(self, repo_owner: str = "jwt625", repo_name: str = "jwt625.github.io", most_recent_only: bool = False, num_posts: int | None = None) -> List[Dict]:
        """Fetch markdown files from _posts directory
        
        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            most_recent_only: If True, only fetch the most recent post
            num_posts: If set, fetch this many most recent posts. Ignored if most_recent_only is True.
        """
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

            # Sort files by date in filename (YYYY-MM-DD-*)
            files.sort(key=lambda x: x["name"].split("-")[:3], reverse=True)

            if most_recent_only:
                files = files[:1]  # Keep only the most recent
                logger.info(f"Selected most recent post: {files[0]['name']}")
            elif num_posts is not None:
                files = files[:num_posts]  # Keep N most recent posts
                logger.info(f"Selected {len(files)} most recent posts")
                logger.debug(f"Selected posts: {[f['name'] for f in files]}")
            
            # Download content for each file with progress tracking
            posts = []
            self.update_progress("downloading", 0, len(files), "Downloading markdown files")
            
            for i, file in enumerate(files, 1):
                raw_url = file["download_url"]
                self.update_progress("downloading", i, len(files), f"Downloading: {file['name']}")
                
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
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            
            return posts

    def _get_existing_post_ids(self) -> Set[str]:
        """Get set of post IDs (GitHub SHAs) that are already in the database"""
        try:
            # Check if collection is empty
            if self.collection.count() == 0:
                logger.info("Collection is empty")
                return set()

            # Query all documents to get their metadata
            results = self.collection.get(
                include=['metadatas']
            )
            
            if not results or 'metadatas' not in results or not results['metadatas']:
                logger.info("No metadata found in collection")
                return set()

            logger.debug(f"Raw metadata results: {results}")
            
            # Extract unique post IDs from metadata
            post_ids = {
                meta.get('post_id') for meta in results['metadatas']
                if meta and 'post_id' in meta and meta.get('post_id') != 'None'
            }
            # Remove None if it got into the set
            post_ids.discard(None)
            
            logger.debug(f"Extracted post_ids: {post_ids}")
            logger.info(f"Found {len(post_ids)} existing posts in database")
            return post_ids
        except Exception as e:
            logger.error(f"Error getting existing post IDs: {e}")
            return set()

    def process_and_store_content(self, posts: List[Dict]) -> int:
        """Process and store content in ChromaDB"""
        logger.info(f"Processing {len(posts)} posts")
        all_chunks = []
        
        # Get existing post IDs
        existing_post_ids = self._get_existing_post_ids()
        logger.debug(f"Posts to process: {[post['id'] for post in posts]}")
        logger.debug(f"Existing post IDs: {existing_post_ids}")
        
        # Process each post into chunks with progress tracking
        self.update_progress("processing", 0, len(posts), "Processing posts into chunks")
        
        for i, post in enumerate(posts, 1):
            if post['id'] in existing_post_ids:
                logger.info(f"Skipping already processed post: {post['name']} (ID: {post['id']})")
                self.update_progress("processing", i, len(posts), f"Skipping already processed post: {post['name']}")
                continue
                
            self.update_progress("processing", i, len(posts), f"Processing new post: {post['name']}")
            chunks = self.text_processor.process_post(post)
            logger.info(f"Generated {len(chunks)} chunks for post: {post['name']}")
            
            # Add post_id to metadata for tracking
            for chunk in chunks:
                chunk["metadata"]["post_id"] = post["id"]
            
            all_chunks.extend(chunks)
        
        # Batch upsert all chunks with progress tracking
        if all_chunks:
            total_chunks = len(all_chunks)
            self.update_progress("storing", 0, total_chunks, "Storing chunks in ChromaDB")
            
            try:
                # Process in batches of 100 to show progress
                batch_size = 100
                for i in range(0, total_chunks, batch_size):
                    batch = all_chunks[i:i + batch_size]
                    self.update_progress("storing", i + len(batch), total_chunks, f"Storing chunks {i+1}-{i+len(batch)}")
                    
                    self.collection.upsert(
                        ids=[chunk["id"] for chunk in batch],
                        documents=[chunk["content"] for chunk in batch],
                        metadatas=[{
                            **chunk["metadata"],
                            "url": chunk["metadata"].get("url", ""),
                            "post_name": str(chunk["metadata"].get("post_name", "")),
                            "chunk_index": str(chunk["metadata"].get("chunk_index", "")),
                            "total_chunks": str(chunk["metadata"].get("total_chunks", "")),
                            "post_id": str(chunk["metadata"].get("post_id", ""))
                        } for chunk in batch]
                    )
                
                self.update_progress("complete", total_chunks, total_chunks, "Successfully stored all chunks")
                logger.info("Successfully stored chunks in ChromaDB")
            except Exception as e:
                logger.error(f"Failed to store chunks in ChromaDB: {str(e)}")
                raise
        else:
            logger.info("No new content to process")
            self.update_progress("complete", 0, 0, "No new content to process")
        
        return len(all_chunks)

    async def update_content(self, most_recent_only: bool = False, num_posts: int | None = None) -> Dict:
        """Update content in ChromaDB
        
        Args:
            most_recent_only: If True, only fetch the most recent post
            num_posts: If set, fetch this many most recent posts. Ignored if most_recent_only is True.
        """
        try:
            logger.info("Starting content update")
            self.update_progress("starting", 0, 0, "Starting content update")
            
            posts = await self.fetch_markdown_content(
                most_recent_only=most_recent_only,
                num_posts=num_posts
            )
            chunk_count = self.process_and_store_content(posts)
            
            result = {
                "status": "success", 
                "message": f"Updated {len(posts)} posts with {chunk_count} chunks",
                "progress": self.get_progress()
            }
            logger.info(result["message"])
            return result
        except Exception as e:
            error_msg = f"Error during content update: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error", 
                "message": error_msg,
                "progress": self.get_progress()
            } 