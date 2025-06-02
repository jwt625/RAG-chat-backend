import pytest
import pytest_asyncio
import logging
from app.rag.ingestion import ContentIngester
from unittest.mock import Mock, AsyncMock, patch
import httpx
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample response data
SAMPLE_FILE_LIST = [
    {
        "name": "2025-05-26-weekly-OFS-48.md",
        "path": "_posts/2025-05-26-weekly-OFS-48.md",
        "sha": "abc123",
        "type": "file",
        "download_url": "https://raw.githubusercontent.com/jwt625/jwt625.github.io/main/_posts/2025-05-26-weekly-OFS-48.md",
        "html_url": "https://github.com/jwt625/jwt625.github.io/blob/main/_posts/2025-05-26-weekly-OFS-48.md"
    }
]

SAMPLE_FILE_CONTENT = """---
layout: post
title: "Weekly OFS #48"
date: 2025-05-26
categories: weekly
tags: [weekly, research, optics]
---

# Weekly Summary

This week's focus was on advanced optical systems and their applications in quantum computing.

## Research Progress

- Completed simulation of quantum optical gates
- Analyzed coherence properties of the system
- Started writing the methods section of the paper

## Next Steps

1. Run additional verification tests
2. Compare results with theoretical predictions
3. Begin drafting the results section
"""

@pytest.fixture
async def mock_httpx():
    """Mock httpx client responses"""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock the context manager
        mock_context = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_context

        # Mock the list files response
        list_response = Mock()
        list_response.status_code = 200
        list_response.json.return_value = SAMPLE_FILE_LIST
        list_response.raise_for_status = Mock()

        # Mock the file content response
        content_response = Mock()
        content_response.status_code = 200
        content_response.text = SAMPLE_FILE_CONTENT
        content_response.raise_for_status = Mock()

        # Set up the mock to return different responses for different URLs
        async def mock_get(url, *args, **kwargs):
            if url.endswith('_posts'):
                return list_response
            else:
                return content_response

        mock_context.get = mock_get
        yield mock_client

@pytest.mark.asyncio
async def test_content_update_with_most_recent(mock_httpx):
    """Test the content update process with most recent post only"""
    logger.info("Starting content update test with most recent post")
    
    # Create ingester with mocked ChromaDB
    with patch('chromadb.PersistentClient') as mock_chroma:
        # Mock collection
        mock_collection = Mock()
        mock_collection.count.return_value = 1
        mock_collection.get.return_value = {
            "documents": ["Sample document content"],
            "metadatas": [{
                "url": "https://github.com/jwt625/jwt625.github.io/blob/main/_posts/2025-05-26-weekly-OFS-48.md",
                "post_name": "2025-05-26-weekly-OFS-48.md",
                "chunk_index": "1",
                "total_chunks": "3"
            }]
        }
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
        
        ingester = ContentIngester()
        
        # Update content with most recent post only
        result = await ingester.update_content(most_recent_only=True)
        assert result["status"] == "success", f"Update failed: {result['message']}"
        
        # Verify content in ChromaDB
        collection = ingester.collection
        count = collection.count()
        logger.info(f"ChromaDB collection has {count} documents")
        assert count > 0, "ChromaDB should contain documents"
        
        # Get and verify the chunks
        results = collection.get()
        assert len(results["documents"]) > 0, "Should have at least one document"
        assert len(results["metadatas"]) > 0, "Documents should have metadata"
        
        # Verify metadata contains expected fields
        metadata = results["metadatas"][0]
        assert "url" in metadata, "Metadata should contain URL"
        assert "post_name" in metadata, "Metadata should contain post name"
        assert "chunk_index" in metadata, "Metadata should contain chunk index"
        
        # Log document details
        for i, (doc, metadata) in enumerate(zip(results["documents"], results["metadatas"])):
            logger.info(f"Document {i+1} metadata: {metadata}")
            logger.debug(f"Document {i+1} content preview:\n{doc[:200]}...")

def test_is_post_file():
    """Test post file name pattern matching"""
    ingester = ContentIngester()
    
    # Valid post filenames
    assert ingester._is_post_file("2025-05-26-weekly-OFS-48.md")
    assert ingester._is_post_file("2024-01-01-test-post.md")
    assert ingester._is_post_file("2023-12-31-end-of-year.md")
    
    # Invalid filenames
    assert not ingester._is_post_file("standard_header.md")
    assert not ingester._is_post_file("2025-5-6-invalid-date.md")  # needs leading zeros
    assert not ingester._is_post_file("2025-05-26-no-extension")
    assert not ingester._is_post_file("not-a-date-post.md")
    assert not ingester._is_post_file("README.md") 