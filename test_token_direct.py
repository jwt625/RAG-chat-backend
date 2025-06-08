#!/usr/bin/env python3
"""Test token extraction directly"""

import httpx
import asyncio

async def test_auth_header():
    """Test if the Authorization header is being read"""
    
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImlkIjoxLCJleHAiOjE3NDkxOTc3NDh9.HCRFQMOGz21Sw93VF46oHR7R9mNSYgLpVQazRVH4N_g"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("🔍 Testing Authorization Header")
    print("="*40)
    print(f"Token: {token[:20]}...")
    print(f"Authorization Header: Bearer {token[:20]}...")
    
    async with httpx.AsyncClient() as client:
        
        # Test the /auth/me endpoint (should be simpler)
        print("\n1. Testing /auth/me endpoint...")
        try:
            response = await client.get("http://localhost:8000/auth/me", headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
            
        # Test the protected RAG endpoint
        print("\n2. Testing /rag/generate endpoint...")
        try:
            data = {"query": "test query", "context_limit": 1}
            response = await client.post("http://localhost:8000/rag/generate", headers=headers, json=data)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth_header())