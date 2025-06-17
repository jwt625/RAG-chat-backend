#!/bin/bash
# Test rate limiting on the /rag/generate-test endpoint (5/minute limit)

echo "🔄 Testing Rate Limit (5 requests/minute on /rag/generate-test)"
echo "=================================================="

SERVER="http://localhost:8000"
ENDPOINT="/rag/generate-test"

for i in {1..7}; do
    echo "Request $i:"
    response=$(curl -s -w "HTTP_STATUS:%{http_code}" -X POST "$SERVER$ENDPOINT" \
        -H "Content-Type: application/json" \
        -d '{"query": "test query", "context_limit": 1}')
    
    http_status=$(echo "$response" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
    body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')
    
    if [ "$http_status" = "429" ]; then
        echo "  ❌ Rate limited! Status: $http_status"
        echo "  📄 Response: $body"
        break
    elif [ "$http_status" = "200" ]; then
        echo "  ✅ Success! Status: $http_status"
    else
        echo "  ⚠️  Other status: $http_status"
        echo "  📄 Response: $body"
    fi
    
    # Small delay between requests
    sleep 1
done

echo ""
echo "Rate limit test completed!"