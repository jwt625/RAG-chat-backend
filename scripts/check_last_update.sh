#!/bin/bash

# Quick script to check when the last update was performed
# Since there's no built-in timestamp tracking, this checks various indicators

set -e

# Configuration
API_BASE_URL="http://localhost:8000"
CREDENTIALS_FILE="$HOME/.chatbot_credentials"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔍 Checking Last Update Information${NC}"
echo "=================================="

# Check 1: ChromaDB directory modification time
echo -e "\n${BLUE}📁 ChromaDB Data Directory:${NC}"
if [[ -d "data/chromadb" ]]; then
    echo "Last modified: $(stat -c %y data/chromadb 2>/dev/null || stat -f %Sm data/chromadb 2>/dev/null || echo 'Unknown')"
    echo "Directory size: $(du -sh data/chromadb 2>/dev/null | cut -f1 || echo 'Unknown')"
else
    echo "❌ ChromaDB directory not found"
fi

# Check 2: Server logs for update activity
echo -e "\n${BLUE}📝 Recent Update Activity in Logs:${NC}"
if [[ -f "server.log" ]]; then
    echo "Recent update-related log entries:"
    grep -i "update\|content\|ingestion" server.log | tail -5 2>/dev/null || echo "No update activity found in logs"
else
    echo "❌ Server log file not found"
fi

# Check 3: Update log files
echo -e "\n${BLUE}📋 Update Log Files:${NC}"
if [[ -d "logs" ]]; then
    UPDATE_LOGS=$(find logs -name "update_*.log" -type f 2>/dev/null | sort -r | head -5)
    if [[ -n "$UPDATE_LOGS" ]]; then
        echo "Recent update logs:"
        echo "$UPDATE_LOGS" | while read -r log_file; do
            echo "  - $log_file ($(stat -c %y "$log_file" 2>/dev/null || stat -f %Sm "$log_file" 2>/dev/null || echo 'Unknown date'))"
        done
    else
        echo "No update log files found"
    fi
else
    echo "❌ Logs directory not found"
fi

# Check 4: Try to get current system status
echo -e "\n${BLUE}📊 Current System Status:${NC}"
STATUS_RESPONSE=$(curl -s "$API_BASE_URL/rag/status" 2>/dev/null || echo "")
if [[ -n "$STATUS_RESPONSE" ]] && [[ "$STATUS_RESPONSE" != *"error"* ]] && [[ "$STATUS_RESPONSE" != *"Unauthorized"* ]]; then
    CURRENT_COUNT=$(echo "$STATUS_RESPONSE" | grep -o '"document_count":[0-9]*' | cut -d':' -f2 || echo "0")
    echo "Current document count: $CURRENT_COUNT"
    echo "Status: $(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo 'Unknown')"
else
    echo "⚠️  Status check requires authentication"
    
    # Try with saved credentials if available
    if [[ -f "$CREDENTIALS_FILE" ]]; then
        echo "Attempting with saved credentials..."
        source "$CREDENTIALS_FILE"
        
        TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE_URL/auth/token" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "username=$USERNAME&password=$PASSWORD" 2>/dev/null || echo "")
        
        if [[ -n "$TOKEN_RESPONSE" ]] && [[ "$TOKEN_RESPONSE" != *"error"* ]]; then
            ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
            
            if [[ -n "$ACCESS_TOKEN" ]]; then
                AUTH_STATUS=$(curl -s -X GET "$API_BASE_URL/rag/status" \
                    -H "Authorization: Bearer $ACCESS_TOKEN" 2>/dev/null || echo "")
                
                if [[ -n "$AUTH_STATUS" ]] && [[ "$AUTH_STATUS" != *"error"* ]]; then
                    CURRENT_COUNT=$(echo "$AUTH_STATUS" | grep -o '"document_count":[0-9]*' | cut -d':' -f2 || echo "0")
                    echo "✅ Current document count: $CURRENT_COUNT"
                    echo "✅ Status: $(echo "$AUTH_STATUS" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo 'Unknown')"
                fi
            fi
        fi
    fi
fi

# Check 5: Process information
echo -e "\n${BLUE}🔄 Server Process Info:${NC}"
SERVER_PID=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | awk '{print $2}' | head -1)
if [[ -n "$SERVER_PID" ]]; then
    echo "Server PID: $SERVER_PID"
    echo "Server started: $(ps -o lstart= -p $SERVER_PID 2>/dev/null || echo 'Unknown')"
    echo "Server uptime: $(ps -o etime= -p $SERVER_PID 2>/dev/null | tr -d ' ' || echo 'Unknown')"
else
    echo "❌ Server process not found"
fi

echo -e "\n${GREEN}💡 Summary:${NC}"
echo "To check for the most recent update activity:"
echo "1. Look at ChromaDB directory modification time above"
echo "2. Check the most recent update log files"
echo "3. Run the update script to see current document count"
echo ""
echo "To perform a new update:"
echo "  ./scripts/update_blog_content.sh"
echo ""
echo "To get detailed status (requires auth):"
echo "  curl -X GET \"$API_BASE_URL/rag/status\" -H \"Authorization: Bearer YOUR_TOKEN\""
