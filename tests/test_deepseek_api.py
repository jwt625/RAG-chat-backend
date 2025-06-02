import pytest
import httpx
from app.config import get_settings
import asyncio
import os

settings = get_settings()

@pytest.mark.asyncio
async def test_deepseek_api_connection():
    """Test basic connection to DeepSeek API"""
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DeepSeek API key not configured")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY.get_secret_value()}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Say 'test' in one word."}],
                "temperature": 0.1,
                "max_tokens": 10
            },
            timeout=30.0
        )
        
        assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
        data = response.json()
        assert "choices" in data, "Response missing 'choices' field"
        assert len(data["choices"]) > 0, "No choices in response"
        assert "message" in data["choices"][0], "Choice missing 'message' field"
        assert "content" in data["choices"][0]["message"], "Message missing 'content' field"
        print(f"\nTest response:\n{data['choices'][0]['message']['content']}")

@pytest.mark.asyncio
async def test_deepseek_api_context_handling():
    """Test DeepSeek API with context-based prompting"""
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DeepSeek API key not configured")
    
    context = """
    Context 1:
    The latest developments in quantum error correction include advances in cat qubits.
    These qubits have shown improved phase-flip times of up to 1 millisecond.
    
    Context 2:
    Traditional quantum error correction requires many physical qubits to create one logical qubit.
    """
    
    query = "What are the latest developments in quantum error correction?"
    
    prompt = f"""You are an AI research assistant helping users find and summarize information from a blog.
    Use the following context to answer the question. Only use information from the provided context.
    
    {context}
    
    Question: {query}
    
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
        
        assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
        data = response.json()
        assert "choices" in data, "Response missing 'choices' field"
        assert len(data["choices"]) > 0, "No choices in response"
        
        generated_text = data["choices"][0]["message"]["content"]
        # Check if the response contains key information from the context
        assert any(term in generated_text.lower() for term in ["cat", "qubit", "error"]), \
            "Response doesn't seem to use the provided context"
        
        print(f"\nGenerated response:\n{generated_text}")

@pytest.mark.asyncio
async def test_deepseek_api_error_handling():
    """Test DeepSeek API error handling"""
    async with httpx.AsyncClient() as client:
        # Test with invalid API key
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": "Bearer invalid_key",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "test"}]
            },
            timeout=30.0
        )
        
        assert response.status_code in [401, 403], \
            "Expected authentication error for invalid API key" 