"""
Full RAG Workflow Integration Test with DeepSeek API

This test demonstrates and validates the complete RAG pipeline:
1. Content ingestion from GitHub blog
2. Vector storage in ChromaDB
3. Context retrieval for user queries
4. LLM generation with DeepSeek API
5. Response formatting and validation

Usage:
    pytest tests/test_full_rag_workflow.py -v -s
    
Required environment variables:
    DEEPSEEK_API_KEY=your_deepseek_api_key
"""

import pytest
import asyncio
import httpx
from unittest.mock import patch, Mock, AsyncMock
from app.config import get_settings
from app.rag.ingestion import ContentIngester
from app.api.rag import SearchQuery, GenerateQuery, generate_response, search_content
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Sample test data
SAMPLE_BLOG_POST = {
    "id": "test_post_123",
    "name": "2025-01-15-quantum-computing-advances.md",
    "content": """---
layout: post
title: "Quantum Computing Advances in 2025"
date: 2025-01-15
categories: quantum
tags: [quantum, computing, research]
---

# Quantum Computing Breakthroughs

This year has seen remarkable advances in quantum computing technology.

## Error Correction Improvements

Recent developments in quantum error correction have achieved:
- Cat qubits with phase-flip times exceeding 1 millisecond
- Improved logical qubit fidelity rates
- Novel surface code implementations

## Applications

The advances enable new applications in:
1. Cryptography and security
2. Drug discovery simulations  
3. Financial modeling optimization

## Future Outlook

The quantum computing landscape continues to evolve rapidly with significant investments from major tech companies.
""",
    "url": "https://github.com/test/test.github.io/blob/main/_posts/2025-01-15-quantum-computing-advances.md"
}

class TestFullRAGWorkflow:
    """Test suite for the complete RAG workflow"""
    
    @pytest.fixture
    async def setup_test_environment(self):
        """Set up test environment with mock data"""
        logger.info("Setting up test environment")
        
        # Mock ChromaDB and ingestion
        with patch('app.rag.ingestion.chromadb.PersistentClient') as mock_chroma:
            mock_collection = Mock()
            mock_collection.count.return_value = 0
            mock_collection.get.return_value = {"documents": [], "metadatas": []}
            mock_collection.upsert = Mock()
            mock_collection.query = Mock()
            
            mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
            
            # Create ingester and add test content
            ingester = ContentIngester()
            
            # Process and store the sample blog post
            chunks = ingester.text_processor.process_post(SAMPLE_BLOG_POST)
            logger.info(f"Generated {len(chunks)} chunks from test post")
            
            # Mock the search results for retrieval
            mock_search_results = [
                {
                    "content": chunk["content"],
                    "metadata": chunk["metadata"],
                    "distance": 0.1 + i * 0.05
                }
                for i, chunk in enumerate(chunks[:3])  # Use first 3 chunks
            ]
            
            # Configure the mock collection to return our test data
            mock_collection.query.return_value = {
                "documents": [[result["content"] for result in mock_search_results]],
                "metadatas": [[result["metadata"] for result in mock_search_results]],
                "distances": [[result["distance"] for result in mock_search_results]]
            }
            
            yield {
                "ingester": ingester,
                "mock_collection": mock_collection,
                "chunks": chunks,
                "search_results": mock_search_results
            }
    
    @pytest.mark.asyncio
    async def test_content_ingestion_and_processing(self, setup_test_environment):
        """Test content ingestion and text processing"""
        test_env = await setup_test_environment
        ingester = test_env["ingester"]
        chunks = test_env["chunks"]
        
        logger.info("Testing content ingestion and processing")
        
        # Verify chunks were created
        assert len(chunks) > 0, "Should generate at least one chunk"
        
        # Verify chunk structure
        for chunk in chunks:
            assert "id" in chunk, "Chunk should have ID"
            assert "content" in chunk, "Chunk should have content"
            assert "metadata" in chunk, "Chunk should have metadata"
            
            # Verify metadata
            metadata = chunk["metadata"]
            assert "title" in metadata, "Metadata should include title"
            assert "categories" in metadata, "Metadata should include categories"
            assert "tags" in metadata, "Metadata should include tags"
            assert "url" in metadata, "Metadata should include URL"
            assert "chunk_index" in metadata, "Metadata should include chunk index"
            
        logger.info(f"✓ Successfully processed {len(chunks)} chunks")
        
        # Verify content quality
        full_content = " ".join(chunk["content"] for chunk in chunks)
        assert "quantum computing" in full_content.lower(), "Content should contain key terms"
        assert "error correction" in full_content.lower(), "Content should contain technical terms"
        
        logger.info("✓ Content ingestion and processing validated")
    
    @pytest.mark.asyncio
    async def test_content_search_and_retrieval(self, setup_test_environment):
        """Test content search and retrieval functionality"""
        test_env = await setup_test_environment
        
        logger.info("Testing content search and retrieval")
        
        # Test search functionality
        with patch('app.api.rag.ingester', test_env["ingester"]):
            search_query = SearchQuery(query="quantum error correction", limit=3)
            search_results = await search_content(search_query)
            
            assert len(search_results) > 0, "Search should return results"
            assert len(search_results) <= 3, "Should respect limit parameter"
            
            # Verify search result structure
            for result in search_results:
                assert hasattr(result, 'content'), "Result should have content"
                assert hasattr(result, 'metadata'), "Result should have metadata"
                assert hasattr(result, 'distance'), "Result should have distance score"
                
            # Verify content relevance
            combined_content = " ".join(result.content for result in search_results)
            assert "quantum" in combined_content.lower(), "Results should be relevant to query"
            
            logger.info(f"✓ Search returned {len(search_results)} relevant results")
    
    @pytest.mark.asyncio
    async def test_deepseek_api_integration(self):
        """Test DeepSeek API integration independently"""
        if not settings.DEEPSEEK_API_KEY:
            pytest.skip("DeepSeek API key not configured")
            
        logger.info("Testing DeepSeek API integration")
        
        test_context = """
        Context from quantum computing blog post:
        
        Recent developments in quantum error correction have achieved cat qubits 
        with phase-flip times exceeding 1 millisecond. This represents a significant 
        improvement in quantum coherence times.
        """
        
        test_query = "What are the recent advances in quantum error correction?"
        
        prompt = f"""You are an AI research assistant helping users find and summarize information from a technical blog.

Use the following context to answer the question:

{test_context}

Question: {test_query}

Answer (remember to cite sources):"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY.get_secret_value()}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30.0
            )
            
            assert response.status_code == 200, f"DeepSeek API failed: {response.text}"
            
            data = response.json()
            assert "choices" in data, "Response should contain choices"
            assert len(data["choices"]) > 0, "Should have at least one choice"
            
            generated_text = data["choices"][0]["message"]["content"]
            assert len(generated_text) > 0, "Should generate non-empty response"
            
            # Verify the response uses the context
            assert any(term in generated_text.lower() for term in ["cat", "qubit", "millisecond"]), \
                "Response should reference the provided context"
                
            logger.info("✓ DeepSeek API integration validated")
            logger.info(f"Generated response preview: {generated_text[:200]}...")
    
    @pytest.mark.asyncio
    async def test_full_rag_generate_workflow(self, setup_test_environment):
        """Test the complete RAG generate workflow end-to-end"""
        if not settings.DEEPSEEK_API_KEY:
            pytest.skip("DeepSeek API key not configured")
            
        test_env = await setup_test_environment
        
        logger.info("Testing complete RAG generate workflow")
        
        # Mock database and authentication dependencies
        mock_db = Mock()
        mock_user = {"id": 1, "username": "test_user"}
        mock_chat = Mock()
        mock_chat.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_chat
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        # Test query
        generate_query = GenerateQuery(
            query="What are the latest advances in quantum error correction?",
            context_limit=3,
            chat_id=1
        )
        
        # Mock the search function to return our test results
        async def mock_search_content(query):
            return [
                Mock(
                    content=result["content"][:500],  # Truncate for testing
                    metadata=result["metadata"],
                    distance=result["distance"]
                )
                for result in test_env["search_results"]
            ]
        
        # Mock the DeepSeek API response
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": """Based on the provided context from the quantum computing blog, recent advances in quantum error correction include:

1. **Cat Qubits**: Significant improvements have been achieved with cat qubits showing phase-flip times exceeding 1 millisecond, representing a major breakthrough in quantum coherence times.

2. **Logical Qubit Fidelity**: The research shows improved logical qubit fidelity rates, which is crucial for building fault-tolerant quantum computers.

3. **Surface Code Implementations**: Novel approaches to surface code implementations have been developed, enhancing error correction capabilities.

These advances enable new applications in cryptography, drug discovery simulations, and financial modeling optimization. [Source: Quantum Computing Advances in 2025 (2025-01-15)]"""
                }
            }]
        }
        
        # Patch all dependencies
        with patch('app.api.rag.search_content', mock_search_content), \
             patch('app.api.rag.get_db', return_value=mock_db), \
             patch('app.api.rag.get_current_user', return_value=mock_user), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Configure HTTP client mock
            mock_context = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_context
            
            mock_http_response = Mock()
            mock_http_response.status_code = 200
            mock_http_response.json.return_value = mock_response_data
            mock_context.post.return_value = mock_http_response
            
            # Import models and patch them
            with patch('app.api.rag.Chat') as MockChat, \
                 patch('app.api.rag.Message') as MockMessage:
                
                MockChat.return_value = mock_chat
                
                # Execute the generate workflow
                result = await generate_response(
                    query=generate_query,
                    db=mock_db,
                    current_user=mock_user
                )
                
                # Validate the response
                assert hasattr(result, 'answer'), "Should return an answer"
                assert hasattr(result, 'context_used'), "Should return context used"
                assert len(result.answer) > 0, "Answer should not be empty"
                assert len(result.context_used) > 0, "Should use context"
                
                # Verify the answer quality
                answer_lower = result.answer.lower()
                assert "cat qubits" in answer_lower, "Answer should mention cat qubits"
                assert "millisecond" in answer_lower, "Answer should mention the time improvement"
                
                # Verify context was properly used
                assert len(result.context_used) <= 3, "Should respect context limit"
                
                logger.info("✓ Full RAG workflow completed successfully")
                logger.info(f"Generated answer preview: {result.answer[:200]}...")
                
    @pytest.mark.asyncio
    async def test_rag_workflow_error_handling(self, setup_test_environment):
        """Test error handling in the RAG workflow"""
        test_env = await setup_test_environment
        
        logger.info("Testing RAG workflow error handling")
        
        # Test with invalid API key
        with patch('app.config.get_settings') as mock_settings:
            mock_settings.return_value.DEEPSEEK_API_KEY = None
            
            mock_db = Mock()
            mock_user = {"id": 1, "username": "test_user"}
            
            generate_query = GenerateQuery(
                query="Test query",
                context_limit=3
            )
            
            with patch('app.api.rag.get_db', return_value=mock_db), \
                 patch('app.api.rag.get_current_user', return_value=mock_user):
                
                with pytest.raises(Exception):  # Should raise HTTPException
                    await generate_response(
                        query=generate_query,
                        db=mock_db,
                        current_user=mock_user
                    )
        
        logger.info("✓ Error handling validation completed")

# Standalone test functions for individual components
@pytest.mark.asyncio
async def test_deepseek_api_basic_functionality():
    """Standalone test for DeepSeek API basic functionality"""
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DeepSeek API key not configured")
    
    logger.info("Testing DeepSeek API basic functionality")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY.get_secret_value()}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Explain quantum computing in one sentence."}],
                "temperature": 0.1,
                "max_tokens": 100
            },
            timeout=30.0
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        
        content = data["choices"][0]["message"]["content"]
        assert "quantum" in content.lower()
        
        logger.info(f"✓ DeepSeek API basic test passed: {content}")

def test_rag_endpoint_imports():
    """Test that all required imports for the RAG endpoint are available"""
    logger.info("Testing RAG endpoint imports")
    
    try:
        from app.api.rag import generate_response, search_content, GenerateQuery, SearchQuery
        from app.config import get_settings
        from app.rag.ingestion import ContentIngester
        from app.rag.text_processing import TextProcessor
        
        logger.info("✓ All RAG endpoint imports successful")
        
        # Test that settings can be loaded
        settings = get_settings()
        assert hasattr(settings, 'DEEPSEEK_API_KEY')
        assert hasattr(settings, 'CHROMA_PERSIST_DIRECTORY')
        
        logger.info("✓ Configuration validation successful")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise

if __name__ == "__main__":
    # Run basic tests
    asyncio.run(test_deepseek_api_basic_functionality())
    test_rag_endpoint_imports()
    print("✓ Basic RAG workflow validation completed")