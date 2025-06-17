#!/usr/bin/env python3
"""Rapid rate limit testing"""

import asyncio
import httpx
import time

async def test_rate_limit():
    """Send rapid requests to test rate limiting"""
    
    url = "http://localhost:8000/rag/generate-test"
    data = {"query": "test", "context_limit": 1}
    
    print("🚀 Rapid Rate Limit Test")
    print("=" * 40)
    
    async with httpx.AsyncClient() as client:
        for i in range(10):
            start_time = time.time()
            try:
                response = await client.post(url, json=data, timeout=10)
                elapsed = time.time() - start_time
                
                print(f"Request {i+1}: Status {response.status_code} ({elapsed:.2f}s)")
                
                if response.status_code == 429:
                    print(f"  🚫 Rate limited! Response: {response.text}")
                    break
                elif response.status_code != 200:
                    print(f"  ⚠️  Error: {response.text}")
                    
            except Exception as e:
                print(f"Request {i+1}: Exception - {e}")
            
            # Very small delay
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(test_rate_limit())