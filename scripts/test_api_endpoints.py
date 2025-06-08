#!/usr/bin/env python3
"""
RAG API Endpoints Test Script

This script demonstrates how to test the RAG API endpoints using HTTP requests.
It shows how to interact with the RAG system as a client would.

Usage:
    # Start the FastAPI server first:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    
    # Then run this script:
    python scripts/test_api_endpoints.py

Environment Requirements:
    DEEPSEEK_API_KEY=your_deepseek_api_key (for generate endpoint)
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

class RAGAPITester:
    """Test client for RAG API endpoints"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=60.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    async def test_rag_status(self) -> Dict[str, Any]:
        """Test GET /rag/status endpoint"""
        print("🔍 Testing RAG Status Endpoint...")
        
        try:
            response = await self.session.get(f"{self.base_url}/rag/status")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ RAG Status Response:")
                print(f"   Status: {data.get('status')}")
                print(f"   Document Count: {data.get('document_count')}")
                print(f"   Collection Name: {data.get('name')}")
                return data
            else:
                print(f"❌ Status endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Status endpoint error: {e}")
            return None
    
    async def test_rag_update(self, most_recent_only=True) -> Dict[str, Any]:
        """Test POST /rag/update endpoint"""
        print(f"📥 Testing RAG Update Endpoint (most_recent_only={most_recent_only})...")
        
        try:
            payload = {
                "most_recent_only": most_recent_only,
                "num_posts": None
            }
            
            response = await self.session.post(
                f"{self.base_url}/rag/update",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ RAG Update Response:")
                print(f"   Status: {data.get('status')}")
                print(f"   Message: {data.get('message')}")
                if 'progress' in data:
                    progress = data['progress']
                    print(f"   Progress: {progress.get('stage')} - {progress.get('current')}/{progress.get('total')}")
                return data
            else:
                print(f"❌ Update endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Update endpoint error: {e}")
            return None
    
    async def test_rag_search(self, query="quantum computing", limit=3) -> Dict[str, Any]:
        """Test POST /rag/search endpoint"""
        print(f"🔍 Testing RAG Search Endpoint (query='{query}', limit={limit})...")
        
        try:
            payload = {
                "query": query,
                "limit": limit
            }
            
            response = await self.session.post(
                f"{self.base_url}/rag/search",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ RAG Search Response: Found {len(data)} results")
                
                for i, result in enumerate(data, 1):
                    print(f"\n--- Result {i} ---")
                    print(f"   Distance: {result.get('distance', 'N/A'):.4f}")
                    print(f"   Source: {result.get('metadata', {}).get('title', 'Unknown')}")
                    print(f"   Date: {result.get('metadata', {}).get('date', 'Unknown')}")
                    print(f"   Content preview: {result.get('content', '')[:150]}...")
                    
                return data
            else:
                print(f"❌ Search endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Search endpoint error: {e}")
            return None
    
    async def test_rag_generate(self, query="What are the latest advances in quantum computing?", context_limit=3) -> Dict[str, Any]:
        """Test POST /rag/generate endpoint"""
        print(f"🤖 Testing RAG Generate Endpoint...")
        print(f"   Query: '{query}'")
        print(f"   Context Limit: {context_limit}")
        
        try:
            payload = {
                "query": query,
                "context_limit": context_limit,
                "chat_id": None,  # Create new chat
                "message_history": None
            }
            
            # Note: This endpoint requires authentication
            # For demo purposes, we'll show what the request looks like
            print("⚠️  Note: Generate endpoint requires authentication (JWT token)")
            print(f"   Request would be: POST {self.base_url}/rag/generate")
            print(f"   Payload: {json.dumps(payload, indent=2)}")
            
            # Uncomment below to test with actual authentication:
            """
            headers = {
                "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
            }
            
            response = await self.session.post(
                f"{self.base_url}/rag/generate",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ RAG Generate Response:")
                print(f"   Answer: {data.get('answer', '')[:200]}...")
                print(f"   Context Used: {len(data.get('context_used', []))} chunks")
                return data
            else:
                print(f"❌ Generate endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
            """
            
            return {"status": "demo_only", "message": "Authentication required for full test"}
                
        except Exception as e:
            print(f"❌ Generate endpoint error: {e}")
            return None
    
    async def test_server_health(self) -> bool:
        """Test if the server is running and responsive"""
        print("🏥 Testing Server Health...")
        
        try:
            response = await self.session.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                print("✅ Server is running and responsive")
                return True
            else:
                print(f"⚠️  Server responded with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Server health check failed: {e}")
            print("   Make sure the FastAPI server is running:")
            print("   uvicorn app.main:app --host 0.0.0.0 --port 8000")
            return False

async def run_complete_api_test():
    """Run complete API endpoint tests"""
    print("🚀 RAG API ENDPOINTS TEST SUITE")
    print("=" * 60)
    
    async with RAGAPITester() as tester:
        # Test server health first
        server_healthy = await tester.test_server_health()
        if not server_healthy:
            return
        
        print("\n" + "=" * 60)
        
        # Test status endpoint
        status_result = await tester.test_rag_status()
        
        print("\n" + "=" * 60)
        
        # Test update endpoint
        update_result = await tester.test_rag_update(most_recent_only=True)
        
        print("\n" + "=" * 60)
        
        # Test search endpoint
        search_result = await tester.test_rag_search(
            query="quantum computing and error correction",
            limit=3
        )
        
        print("\n" + "=" * 60)
        
        # Test generate endpoint (demo only due to auth requirements)
        generate_result = await tester.test_rag_generate(
            query="What are the recent developments in quantum error correction?",
            context_limit=3
        )
        
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        results = {
            "Server Health": "✅" if server_healthy else "❌",
            "Status Endpoint": "✅" if status_result else "❌", 
            "Update Endpoint": "✅" if update_result else "❌",
            "Search Endpoint": "✅" if search_result else "❌",
            "Generate Endpoint": "🔒 Auth Required"
        }
        
        for test, status in results.items():
            print(f"   {test}: {status}")
        
        print("\n💡 NEXT STEPS:")
        print("   1. To test the generate endpoint, you need to:")
        print("      - Set up user authentication")
        print("      - Obtain a JWT token")
        print("      - Add Authorization header to requests")
        print("   2. Check the FastAPI docs at http://localhost:8000/docs")
        print("   3. Review the authentication setup in app/security.py")

def generate_curl_examples():
    """Generate curl command examples for testing"""
    print("\n" + "🔧 CURL COMMAND EXAMPLES")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    examples = [
        {
            "name": "Test RAG Status",
            "command": f"curl -X GET '{base_url}/rag/status'"
        },
        {
            "name": "Update Content (Most Recent Only)",
            "command": f"""curl -X POST '{base_url}/rag/update' \\
  -H 'Content-Type: application/json' \\
  -d '{{"most_recent_only": true, "num_posts": null}}'"""
        },
        {
            "name": "Search Content",
            "command": f"""curl -X POST '{base_url}/rag/search' \\
  -H 'Content-Type: application/json' \\
  -d '{{"query": "quantum computing", "limit": 3}}'"""
        },
        {
            "name": "Generate Response (Requires Auth)",
            "command": f"""curl -X POST '{base_url}/rag/generate' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer YOUR_JWT_TOKEN' \\
  -d '{{"query": "What is quantum computing?", "context_limit": 3}}'"""
        }
    ]
    
    for example in examples:
        print(f"\n{example['name']}:")
        print(f"  {example['command']}")

async def main():
    """Main function"""
    try:
        await run_complete_api_test()
        generate_curl_examples()
        
    except KeyboardInterrupt:
        print("\n\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")

if __name__ == "__main__":
    asyncio.run(main())