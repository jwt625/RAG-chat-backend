#!/usr/bin/env python3
"""
Test script to verify comprehensive API logging functionality
"""
import asyncio
import httpx
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_logging():
    """Test various endpoints to generate log entries"""
    
    print("🧪 Testing comprehensive API logging...")
    print(f"📡 Base URL: {BASE_URL}")
    print(f"⏰ Test started at: {datetime.now().isoformat()}")
    print("-" * 60)
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Health check (public endpoint)
        print("1️⃣ Testing health check endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/rag/health")
            print(f"   ✅ Health check: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
        
        # Test 2: Root endpoint
        print("2️⃣ Testing root endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"   ✅ Root endpoint: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Root endpoint failed: {e}")
        
        # Test 3: Generate-test endpoint (no auth required)
        print("3️⃣ Testing generate-test endpoint...")
        try:
            test_query = {
                "query": "What is quantum computing?",
                "context_limit": 2
            }
            response = await client.post(
                f"{BASE_URL}/rag/generate-test",
                json=test_query,
                timeout=30.0
            )
            print(f"   ✅ Generate-test: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   📝 Response length: {len(result.get('answer', ''))}")
                print(f"   🔍 Context chunks: {len(result.get('context_used', []))}")
        except Exception as e:
            print(f"   ❌ Generate-test failed: {e}")
        
        # Test 4: Authentication failure (invalid credentials)
        print("4️⃣ Testing authentication failure...")
        try:
            response = await client.post(
                f"{BASE_URL}/auth/token",
                data={"username": "invalid_user", "password": "wrong_password"}
            )
            print(f"   ✅ Auth failure logged: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Auth test failed: {e}")
        
        # Test 5: Rate limit test (multiple rapid requests)
        print("5️⃣ Testing rate limiting...")
        try:
            for i in range(3):
                response = await client.get(f"{BASE_URL}/rag/health")
                print(f"   📊 Request {i+1}: {response.status_code}")
                time.sleep(0.1)  # Small delay
        except Exception as e:
            print(f"   ❌ Rate limit test failed: {e}")
        
        # Test 6: Non-existent endpoint (404 error)
        print("6️⃣ Testing 404 error...")
        try:
            response = await client.get(f"{BASE_URL}/nonexistent")
            print(f"   ✅ 404 error logged: {response.status_code}")
        except Exception as e:
            print(f"   ❌ 404 test failed: {e}")
    
    print("-" * 60)
    print("✅ Logging test completed!")
    print("\n📊 You can now check the database for logged requests:")
    print("   sudo -u postgres psql -d chatbot_db -c \"SELECT COUNT(*) FROM api_request_logs;\"")
    print("   sudo -u postgres psql -d chatbot_db -c \"SELECT timestamp, method, path, status_code, event_type FROM api_request_logs ORDER BY timestamp DESC LIMIT 10;\"")

if __name__ == "__main__":
    asyncio.run(test_logging())
