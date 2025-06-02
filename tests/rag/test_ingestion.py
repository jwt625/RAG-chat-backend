import pytest
from unittest.mock import Mock, patch
import httpx
import json
from app.rag.ingestion import ContentIngester

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

@pytest.fixture
async def mock_httpx_client():
    with patch('httpx.AsyncClient') as mock_client:
        # Mock the context manager
        mock_cm = Mock()
        mock_client.return_value.__aenter__.return_value = mock_cm
        
        # Create async mock responses
        files_response = Mock()
        files_response.status_code = 200
        files_response.json.return_value = MOCK_FILES_RESPONSE
        
        content_response = Mock()
        content_response.status_code = 200
        content_response.text = MOCK_FILE_CONTENT
        
        # Make get return a coroutine
        async def mock_get(*args, **kwargs):
            if "_posts" in args[0]:
                return files_response
            return content_response
            
        mock_cm.get = mock_get
        yield mock_client

@pytest.fixture
def mock_chromadb():
    with patch('chromadb.PersistentClient') as mock_client:
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        yield mock_client

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
        error_response = Mock()
        error_response.status_code = 403
        error_response.text = "API rate limit exceeded"
        return error_response
        
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
    ingester = ContentIngester()
    result = await ingester.update_content()
    
    assert result["status"] == "success"
    assert "Updated 1 posts" in result["message"]

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