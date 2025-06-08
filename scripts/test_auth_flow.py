#!/usr/bin/env python3
"""
Authentication Flow Test Script

This script demonstrates how to:
1. Register a new user
2. Login to get access token
3. Use token to access protected endpoints

Usage:
    python scripts/test_auth_flow.py
"""

import httpx
import json
import asyncio
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:8000"

async def test_auth_flow():
    """Test the complete authentication flow"""
    
    print("🔐 Testing Authentication Flow")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Register a new user
        print("\n1. Registering new user...")
        
        user_data = {
            "username": "testuser",
            "email": "test@example.com", 
            "password": "testpassword123"
        }
        
        try:
            response = await client.post(f"{BASE_URL}/auth/register", json=user_data)
            if response.status_code == 200:
                print("✅ User registered successfully")
                print(f"   Response: {response.json()}")
            elif response.status_code == 400:
                print("⚠️  User already exists (expected if running multiple times)")
                print(f"   Response: {response.json()}")
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return
        
        # Test 2: Login to get access token
        print("\n2. Logging in to get access token...")
        
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/auth/token",
                data=login_data,  # OAuth2PasswordRequestForm expects form data
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data["access_token"]
                print("✅ Login successful")
                print(f"   Access token: {access_token[:20]}...")
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return
        except Exception as e:
            print(f"❌ Login error: {e}")
            return
        
        # Test 3: Test protected endpoint without token
        print("\n3. Testing protected endpoint without token...")
        
        try:
            response = await client.post(
                f"{BASE_URL}/rag/generate",
                json={"query": "test query", "context_limit": 1}
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 4: Test protected endpoint with token
        print("\n4. Testing protected endpoint with token...")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = await client.post(
                f"{BASE_URL}/rag/generate",
                json={
                    "query": "What are recent developments in quantum computing?",
                    "context_limit": 2
                },
                headers=headers
            )
            
            if response.status_code == 200:
                print("✅ Protected endpoint access successful")
                result = response.json()
                print(f"   Answer preview: {result['answer'][:200]}...")
                print(f"   Context chunks used: {len(result['context_used'])}")
            else:
                print(f"❌ Protected endpoint failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Protected endpoint error: {e}")
        
        # Test 5: Get current user info
        print("\n5. Getting current user info...")
        
        try:
            response = await client.get(f"{BASE_URL}/auth/me", headers=headers)
            
            if response.status_code == 200:
                print("✅ User info retrieved")
                print(f"   User: {response.json()}")
            else:
                print(f"❌ User info failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ User info error: {e}")

def print_curl_examples():
    """Print curl examples for manual testing"""
    
    print("\n" + "="*60)
    print("📋 CURL EXAMPLES FOR MANUAL TESTING")
    print("="*60)
    
    print("\n1. Register user:")
    print('curl -X POST "http://localhost:8000/auth/register" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"username": "testuser", "email": "test@example.com", "password": "testpassword123"}\'')
    
    print("\n2. Login (get token):")
    print('curl -X POST "http://localhost:8000/auth/token" \\')
    print('  -H "Content-Type: application/x-www-form-urlencoded" \\')
    print('  -d "username=testuser&password=testpassword123"')
    
    print("\n3. Use protected endpoint:")
    print('curl -X POST "http://localhost:8000/rag/generate" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\')
    print('  -d \'{"query": "What are recent developments in quantum computing?", "context_limit": 2}\'')
    
    print("\n4. Get user info:")
    print('curl -X GET "http://localhost:8000/auth/me" \\')
    print('  -H "Authorization: Bearer YOUR_TOKEN_HERE"')

async def main():
    """Main function"""
    try:
        await test_auth_flow()
        print_curl_examples()
        print("\n✅ Authentication flow test completed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())