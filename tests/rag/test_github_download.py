import pytest
import httpx
import logging
import os
from datetime import datetime
from pathlib import Path

# Set up log directory
log_dir = Path(__file__).parent.parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)

# Configure logger
logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def setup_logging(request):
    """Set up logging for each test"""
    log_file = log_dir / f'test_github_download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    
    # Log test start
    logger.info(f"Starting test: {request.node.name}")
    logger.info(f"Logging to: {log_file}")
    
    yield
    
    # Log test end and clean up
    logger.info(f"Finished test: {request.node.name}")
    logger.removeHandler(file_handler)
    file_handler.close()

async def fetch_markdown_content(repo_owner: str, repo_name: str) -> list:
    """Fetch all markdown files from _posts directory"""
    async with httpx.AsyncClient() as client:
        # Get list of markdown files
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/_posts"
        logger.info(f"Fetching files from: {api_url}")
        
        response = await client.get(
            api_url,
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        response.raise_for_status()
        
        files = [f for f in response.json() if f["type"] == "file" and f["name"].endswith(".md")]
        logger.info(f"Found {len(files)} markdown files")
        
        # Download content for each file
        posts = []
        for file in files:
            raw_url = file["download_url"]
            logger.info(f"Downloading: {file['name']}")
            
            content_response = await client.get(raw_url)
            content_response.raise_for_status()
            
            posts.append({
                "id": file["sha"],
                "name": file["name"],
                "content": content_response.text,
                "url": file["html_url"]
            })
            logger.debug(f"Content preview for {file['name']}:\n{content_response.text[:200]}...")
        
        return posts

@pytest.mark.asyncio
async def test_fetch_blog_content():
    """Test downloading markdown content from the blog"""
    logger.info("Starting blog content fetch test")
    posts = await fetch_markdown_content("jwt625", "jwt625.github.io")
    
    # Basic validation
    assert len(posts) > 0, "Should find markdown files"
    logger.info(f"Found {len(posts)} total posts")
    
    # Check first post structure
    post = posts[0]
    logger.info(f"First post: {post['name']}")
    logger.debug(f"Content preview:\n{post['content'][:200]}")
    
    assert post["content"].startswith("---"), "Should be a Jekyll markdown file"
    assert len(post["content"]) > 0, "Should have content"
    logger.info("Test completed successfully") 