# RFD-002: Mobile Browser CORS Preflight Fix

**Date**: 2025-07-24  
**Status**: Implemented  
**Author**: System Administrator  

## Summary

Fixed CORS preflight request failures for mobile browsers (Safari and Firefox on iPhone) that were returning status 400 for OPTIONS requests to the `/rag/generate-test` endpoint. The root cause was Nginx not handling OPTIONS requests, causing them to reach the FastAPI application where they were being rejected by the rate limiter.

## Problem

Mobile browsers were failing with the error:
```
Preflight response is not successful. Status code: 400
Fetch API cannot load https://rag-api.outside5sigma.com/rag/generate-test due to access control checks.
```

The API server was returning status 400 for CORS preflight (OPTIONS) requests, which mobile browsers send before POST requests.

## Root Cause Analysis

The issue had multiple layers:
1. **Nginx was not handling CORS** - No CORS headers or OPTIONS handling in Nginx configuration
2. **Rate limiter was blocking OPTIONS requests** - FastAPI rate limiter was returning 400 for preflight requests
3. **Mobile browsers strictly enforce CORS** - Unlike desktop browsers, mobile Safari/Firefox require proper preflight handling

## Solution

### 1. Updated Nginx Configuration (Primary Fix)
Added CORS handling directly in Nginx to intercept OPTIONS requests before they reach FastAPI:
- OPTIONS requests now return 204 No Content with proper CORS headers
- Nginx passes through CORS headers from upstream for other requests
- This prevents rate limiter from blocking preflight requests

### 2. Updated CORS Middleware Configuration
- Set `allow_credentials=False` for better mobile compatibility
- Specified explicit allowed methods: `["GET", "POST", "OPTIONS"]`
- Specified explicit allowed headers: `["Content-Type", "Accept", "Authorization"]`
- Added `max_age=86400` to cache preflight requests for 24 hours

### 3. Added Explicit OPTIONS Handlers (Backup)
- Specific handler for `/rag/generate-test` endpoint
- Generic handler for all `/rag/*` endpoints  
- Both handlers return status 200 with proper CORS headers
- These serve as backup if Nginx doesn't handle OPTIONS

### 4. Added Request Logging
- Added middleware to log all requests for debugging CORS issues
- Logs method, URL, origin, and response status
- Helps identify where requests are being blocked

### 5. Updated Generate-Test Endpoint
- Modified to return explicit CORS headers in JSONResponse
- Dynamically sets `Access-Control-Allow-Origin` based on request origin
- Ensures CORS headers are present even if middleware fails

## Implementation Details

### Files Modified

1. **/etc/nginx/sites-available/chatbot-api** (Primary Fix)
   - Added OPTIONS request handling with 204 response
   - Added CORS headers for preflight requests
   - Added proxy_pass_header directives for CORS headers

2. **app/main.py**
   - Updated CORS middleware configuration
   - Added request logging middleware
   - Added OPTIONS handlers for preflight requests

3. **app/api/rag.py**
   - Added JSONResponse import
   - Modified generate-test endpoint to return explicit CORS headers

### Code Changes

#### Nginx CORS Configuration (Primary Fix)
```nginx
location / {
    # Handle OPTIONS requests
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' '$http_origin' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Accept, Authorization' always;
        add_header 'Access-Control-Max-Age' 86400 always;
        add_header 'Content-Length' 0;
        add_header 'Content-Type' 'text/plain' always;
        return 204;
    }

    proxy_pass http://127.0.0.1:8000;
    # ... other proxy settings ...
    
    # Pass CORS headers from upstream
    proxy_pass_header Access-Control-Allow-Origin;
    proxy_pass_header Access-Control-Allow-Methods;
    proxy_pass_header Access-Control-Allow-Headers;
}
```

#### CORS Middleware Update
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,  # Changed from True
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    max_age=86400,  # Cache preflight for 24 hours
)
```

#### OPTIONS Handler
```python
@app.options("/rag/generate-test")
async def preflight_handler_generate_test(request: Request):
    """Handle CORS preflight requests for mobile browsers"""
    origin = request.headers.get("origin", "*")
    
    if origin in settings.CORS_ORIGINS or "*" in settings.CORS_ORIGINS:
        allowed_origin = origin
    else:
        allowed_origin = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "*"
    
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Accept",
            "Access-Control-Max-Age": "86400",
        }
    )
```

#### Generate-Test Endpoint Update
```python
return JSONResponse(
    content=response_data.dict(),
    headers={
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Accept",
    }
)
```

## Testing

To apply and test the fix:
1. Reload Nginx configuration: `sudo systemctl reload nginx`
2. Restart the FastAPI server
3. Test from iPhone Safari/Firefox
4. Monitor logs for OPTIONS requests returning 204 from Nginx
5. Verify successful POST requests following preflight

## Troubleshooting

If the issue persists:
1. Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
2. Check FastAPI logs for OPTIONS requests (should not see them if Nginx handles them)
3. Verify Nginx configuration is valid: `sudo nginx -t`
4. Ensure allowed origins in settings match the request origin

## Notes

- The primary fix is at the Nginx level, preventing OPTIONS requests from reaching FastAPI
- Mobile browsers are more strict about CORS than desktop browsers
- OPTIONS requests must return 2xx status (204 or 200) for preflight to succeed
- The FastAPI-level fixes serve as fallback if Nginx configuration is bypassed
- Setting `allow_credentials=False` improves mobile browser compatibility when cookies aren't needed

## Key Learnings

1. **Layer CORS handling** - Handle CORS at the reverse proxy level when possible
2. **Rate limiters must exclude OPTIONS** - Preflight requests should never be rate limited
3. **Mobile browsers enforce strict CORS** - Test on actual mobile devices, not just desktop browser dev tools
4. **204 No Content is ideal for OPTIONS** - Minimal response for preflight requests

## Future Considerations

- Consider implementing more granular CORS policies per endpoint
- Add monitoring specifically for CORS preflight failures
- Document CORS configuration in both Nginx and FastAPI for consistency
- Consider creating a health check endpoint that tests CORS functionality