#!/usr/bin/env python3
"""Complete authentication test and documentation"""

import httpx
import asyncio
import json

async def complete_auth_test():
    """Test complete authentication flow"""
    
    print("🔐 COMPLETE AUTHENTICATION TEST")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        
        # Step 1: Login to get token
        print("\n1. Getting fresh access token...")
        login_response = await client.post(
            "http://localhost:8000/auth/token",
            data={"username": "testuser", "password": "testpassword123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code} - {login_response.text}")
            return
            
        token_data = login_response.json()
        access_token = token_data["access_token"]
        print(f"✅ Token received: {access_token[:20]}...")
        
        # Step 2: Test /auth/me endpoint
        print("\n2. Testing /auth/me endpoint...")
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        me_response = await client.get("http://localhost:8000/auth/me", headers=auth_headers)
        print(f"   Status: {me_response.status_code}")
        print(f"   Response: {me_response.text}")
        
        if me_response.status_code != 200:
            print("❌ /auth/me failed - authentication not working")
            return
            
        # Step 3: Test protected RAG endpoint
        print("\n3. Testing protected RAG endpoint...")
        rag_data = {
            "query": "What are recent developments in quantum computing?",
            "context_limit": 2
        }
        
        rag_response = await client.post(
            "http://localhost:8000/rag/generate",
            json=rag_data,
            headers=auth_headers
        )
        
        print(f"   Status: {rag_response.status_code}")
        if rag_response.status_code == 200:
            print("✅ Protected RAG endpoint working!")
            result = rag_response.json()
            print(f"   Answer preview: {result['answer'][:200]}...")
            print(f"   Context chunks: {len(result['context_used'])}")
        else:
            print(f"❌ Protected RAG endpoint failed: {rag_response.text}")
            
        # Step 4: Test without token
        print("\n4. Testing endpoint without token (should fail)...")
        no_auth_response = await client.post(
            "http://localhost:8000/rag/generate",
            json=rag_data
        )
        print(f"   Status: {no_auth_response.status_code}")
        print(f"   Response: {no_auth_response.text}")
        
        return access_token

def print_auth_summary(token=None):
    """Print authentication setup summary"""
    
    print("\n" + "=" * 60)
    print("🎯 AUTHENTICATION SETUP SUMMARY")
    print("=" * 60)
    
    print("\n📋 **For Testing the Production RAG Endpoint:**")
    
    print("\n1. **Register a user** (if needed):")
    print('   curl -X POST "http://localhost:8000/auth/register" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"username": "your_username", "email": "your@email.com", "password": "your_password"}\'')
    
    print("\n2. **Login to get access token:**")
    print('   curl -X POST "http://localhost:8000/auth/token" \\')
    print('     -H "Content-Type: application/x-www-form-urlencoded" \\')
    print('     -d "username=your_username&password=your_password"')
    
    print("\n3. **Use the token for protected endpoints:**")
    print('   curl -X POST "http://localhost:8000/rag/generate" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\')
    print('     -d \'{"query": "Your question here", "context_limit": 3}\'')
    
    if token:
        print(f"\n🔑 **Current Valid Token:**")
        print(f"   {token}")
    
    print("\n📚 **Available Endpoints:**")
    print("   • POST /auth/register - Register new user")
    print("   • POST /auth/token - Login and get JWT token")
    print("   • GET /auth/me - Get current user info (requires auth)")
    print("   • POST /rag/generate - Full RAG with auth and chat history")
    print("   • POST /rag/generate-test - RAG without auth (for testing)")
    print("   • POST /rag/search - Search content (no auth)")
    print("   • POST /rag/update - Update content (no auth)")
    print("   • GET /rag/status - System status (no auth)")
    
    print("\n🚀 **For Production Use:**")
    print("   - Users register once, then login to get tokens")
    print("   - Tokens expire after 30 minutes (configurable)")
    print("   - Chat conversations are saved to database")
    print("   - Rate limiting: 20 requests per minute per IP")
    print("   - Full conversation history and RAG context tracking")

async def main():
    """Main function"""
    try:
        token = await complete_auth_test()
        print_auth_summary(token)
        print("\n✅ Complete authentication test finished!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())