#!/usr/bin/env python3
"""Debug JWT token"""

import jwt
import base64
import json
from app.config import get_settings

settings = get_settings()

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImlkIjoxLCJleHAiOjE3NDkxOTc3NDh9.HCRFQMOGz21Sw93VF46oHR7R9mNSYgLpVQazRVH4N_g"

print("🔍 Debugging JWT Token")
print("="*50)

# Decode without verification first
try:
    decoded = jwt.decode(token, options={"verify_signature": False})
    print("✅ Token payload (unverified):")
    print(json.dumps(decoded, indent=2))
except Exception as e:
    print(f"❌ Error decoding token: {e}")

# Try to decode with verification
try:
    decoded = jwt.decode(
        token, 
        settings.JWT_SECRET_KEY.get_secret_value(), 
        algorithms=[settings.JWT_ALGORITHM]
    )
    print("✅ Token payload (verified):")
    print(json.dumps(decoded, indent=2))
except jwt.ExpiredSignatureError:
    print("❌ Token has expired")
except jwt.InvalidTokenError as e:
    print(f"❌ Invalid token: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

print(f"\nJWT Secret: {settings.JWT_SECRET_KEY.get_secret_value()[:10]}...")
print(f"JWT Algorithm: {settings.JWT_ALGORITHM}")