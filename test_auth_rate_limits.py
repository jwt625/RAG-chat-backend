#!/usr/bin/env python3
"""Test rate limits on authenticated endpoints"""

import asyncio
import httpx

async def get_token():
    """Get JWT token for testing"""
    async with httpx.AsyncClient() as client:
        # Login to get token
        response = await client.post(
            "http://localhost:8000/auth/token",
            data={"username": "testuser", "password": "testpassword123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None

async def test_status_rate_limit(token):
    """Test /rag/status rate limit (30/minute)"""
    print("\n🔍 Testing /rag/status rate limit (30/minute)")
    print("-" * 50)
    
    headers = {"Authorization": f"Bearer {token}"}
    url = "http://localhost:8000/rag/status"
    
    async with httpx.AsyncClient() as client:
        for i in range(35):  # Try to exceed 30/minute
            try:
                response = await client.get(url, headers=headers, timeout=5)
                if response.status_code == 429:
                    print(f"  Request {i+1}: 🚫 Rate limited! {response.text}")
                    break
                elif response.status_code == 200:
                    print(f"  Request {i+1}: ✅ Success")
                else:
                    print(f"  Request {i+1}: ⚠️ Status {response.status_code}")
                    
            except Exception as e:
                print(f"  Request {i+1}: Exception - {e}")
            
            await asyncio.sleep(0.1)  # Rapid fire

async def test_search_rate_limit(token):
    """Test /rag/search rate limit (20/minute)"""
    print("\n🔍 Testing /rag/search rate limit (20/minute)")
    print("-" * 50)
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = "http://localhost:8000/rag/search"
    data = {"query": "test", "limit": 1}
    
    async with httpx.AsyncClient() as client:
        for i in range(25):  # Try to exceed 20/minute
            try:
                response = await client.post(url, headers=headers, json=data, timeout=5)
                if response.status_code == 429:
                    print(f"  Request {i+1}: 🚫 Rate limited! {response.text}")
                    break
                elif response.status_code == 200:
                    print(f"  Request {i+1}: ✅ Success")
                else:
                    print(f"  Request {i+1}: ⚠️ Status {response.status_code}")
                    
            except Exception as e:
                print(f"  Request {i+1}: Exception - {e}")
            
            await asyncio.sleep(0.1)

async def main():
    print("🔐 Testing Authenticated Endpoint Rate Limits")
    print("=" * 60)
    
    # Get token
    token = await get_token()
    if not token:
        print("❌ Could not get authentication token")
        return
    
    print(f"✅ Got token: {token[:20]}...")
    
    # Test different endpoints
    await test_status_rate_limit(token)
    await test_search_rate_limit(token)
    
    print("\n✅ Rate limit testing completed!")

if __name__ == "__main__":
    asyncio.run(main())