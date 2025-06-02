import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, PropertyMock
import httpx
import json
import logging
from app.rag.ingestion import ContentIngester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock data for tests
MOCK_FILES_RESPONSE = [
    {
        "name": "2024-01-01-test-post.md",
        "type": "file",
        "sha": "abc123",
        "html_url": "https://github.com/jwt625/jwt625.github.io/blob/master/_posts/2024-01-01-test-post.md"
    }
]

MOCK_FILE_CONTENT = """---
layout: post
title: Test Post
date: 2024-01-01
categories: test
---
# Test Content
This is a test blog post content."""

@pytest_asyncio.fixture
async def mock_httpx_client():
    with patch('httpx.AsyncClient') as mock_client:
        mock_cm = Mock()
        mock_client.return_value.__aenter__.return_value = mock_cm
        
        # Create mock responses with proper async behavior
        async def mock_get(*args, **kwargs):
            if "_posts" in args[0]:
                response = Mock()
                response.status_code = 200
                response.json.return_value = MOCK_FILES_RESPONSE
                return response
            else:
                response = Mock()
                response.status_code = 200
                # Use property mock to ensure text attribute works correctly
                type(response).text = PropertyMock(return_value=MOCK_FILE_CONTENT)
                return response
            
        mock_cm.get = mock_get
        yield mock_client

@pytest.fixture
def mock_chromadb():
    with patch('chromadb.PersistentClient') as mock_client:
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        # Ensure upsert doesn't raise any exceptions
        mock_collection.upsert.return_value = None
        yield mock_client

@pytest.fixture
def ingester():
    """Create a ContentIngester instance"""
    logger.info("Creating ContentIngester for test")
    return ContentIngester()

@pytest.mark.asyncio
async def test_fetch_content_from_github(mock_httpx_client):
    ingester = ContentIngester()
    posts = await ingester.fetch_content_from_github()
    
    assert len(posts) == 1
    assert posts[0]["name"] == "2024-01-01-test-post.md"
    assert posts[0]["content"] == MOCK_FILE_CONTENT
    assert posts[0]["url"] == MOCK_FILES_RESPONSE[0]["html_url"]

@pytest.mark.asyncio
async def test_fetch_content_from_github_api_error(mock_httpx_client):
    # Mock API error response
    async def mock_error_get(*args, **kwargs):
        response = Mock()
        response.status_code = 403
        response.text = "API rate limit exceeded"
        return response
        
    mock_client = mock_httpx_client.return_value.__aenter__.return_value
    mock_client.get = mock_error_get
    
    ingester = ContentIngester()
    with pytest.raises(Exception) as exc_info:
        await ingester.fetch_content_from_github()
    assert "Failed to fetch repository contents" in str(exc_info.value)

def test_process_and_store_content(mock_chromadb):
    ingester = ContentIngester()
    test_posts = [{
        "id": "abc123",
        "name": "2024-01-01-test-post.md",
        "content": MOCK_FILE_CONTENT,
        "url": "https://github.com/jwt625/jwt625.github.io/blob/master/_posts/2024-01-01-test-post.md"
    }]
    
    chunk_count = ingester.process_and_store_content(test_posts)
    assert chunk_count > 0
    
    # Verify ChromaDB collection was called with correct data
    collection = mock_chromadb.return_value.get_or_create_collection.return_value
    assert collection.upsert.called

@pytest.mark.asyncio
async def test_update_content_success(mock_httpx_client, mock_chromadb):
    # Set up mock collection to return success
    mock_collection = mock_chromadb.return_value.get_or_create_collection.return_value
    mock_collection.upsert.return_value = None  # Successful upsert returns None
    
    ingester = ContentIngester()
    result = await ingester.update_content()
    
    assert result["status"] == "success"
    assert "Updated 1 posts" in result["message"]
    assert mock_collection.upsert.called

@pytest.mark.asyncio
async def test_update_content_failure(mock_httpx_client):
    # Mock API error
    async def mock_error_get(*args, **kwargs):
        raise Exception("Network error")
        
    mock_client = mock_httpx_client.return_value.__aenter__.return_value
    mock_client.get = mock_error_get
    
    ingester = ContentIngester()
    result = await ingester.update_content()
    
    assert result["status"] == "error"
    assert "Network error" in result["message"]

@pytest.mark.asyncio
async def test_content_update(ingester):
    """Test the full content update process"""
    logger.info("Starting content update test")
    
    # Update content
    result = await ingester.update_content()
    assert result["status"] == "success", f"Update failed: {result['message']}"
    
    # Verify the result contains expected information
    assert "posts" in result["message"], "Result should mention number of posts"
    assert "chunks" in result["message"], "Result should mention number of chunks"
    
    logger.info(f"Update result: {result['message']}")
    
    # Verify content in ChromaDB
    collection = ingester.collection
    count = collection.count()
    logger.info(f"ChromaDB collection has {count} documents")
    assert count > 0, "ChromaDB should contain documents"
    
    # Get a sample document to verify structure
    results = collection.get(limit=1)
    assert len(results["documents"]) > 0, "Should be able to retrieve a document"
    assert len(results["metadatas"]) > 0, "Document should have metadata"
    
    # Log sample document details
    doc = results["documents"][0]
    metadata = results["metadatas"][0]
    logger.info(f"Sample document metadata: {metadata}")
    logger.debug(f"Sample document content preview:\n{doc[:200]}...") 