#!/bin/bash

# Blog Content Update Script
# This script performs a step-by-step update of the RAG chatbot content from the blog

set -e  # Exit on any error

# Configuration
API_BASE_URL="http://localhost:8000"
CREDENTIALS_FILE="$HOME/.chatbot_credentials"
LOG_FILE="./logs/update_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "${RED}❌ ERROR: $1${NC}"
    exit 1
}

# Success message
success() {
    log "${GREEN}✅ $1${NC}"
}

# Info message
info() {
    log "${BLUE}ℹ️  $1${NC}"
}

# Warning message
warn() {
    log "${YELLOW}⚠️  $1${NC}"
}

# Create logs directory if it doesn't exist
mkdir -p logs

log "${BLUE}🚀 Starting Blog Content Update Process${NC}"
log "📅 $(date)"
log "📝 Log file: $LOG_FILE"
echo ""

# Step 1: Check if server is running
info "Step 1: Checking if server is running..."
if ! curl -s "$API_BASE_URL/" > /dev/null; then
    error_exit "Server is not running at $API_BASE_URL. Please start the server first."
fi
success "Server is running"

# Step 2: Check current system status (before update)
info "Step 2: Checking current system status..."
STATUS_RESPONSE=$(curl -s "$API_BASE_URL/rag/status" || echo "")
if [[ -n "$STATUS_RESPONSE" ]]; then
    CURRENT_COUNT=$(echo "$STATUS_RESPONSE" | grep -o '"document_count":[0-9]*' | cut -d':' -f2 || echo "0")
    info "Current document count: $CURRENT_COUNT"
else
    warn "Could not get status (authentication may be required)"
fi

# Step 3: Get credentials
info "Step 3: Getting authentication credentials..."

# Check if credentials file exists
if [[ -f "$CREDENTIALS_FILE" ]]; then
    source "$CREDENTIALS_FILE"
    info "Using saved credentials from $CREDENTIALS_FILE"
else
    echo ""
    read -p "Enter username: " USERNAME
    read -s -p "Enter password: " PASSWORD
    echo ""
    
    # Optionally save credentials
    read -p "Save credentials for future use? (y/n): " SAVE_CREDS
    if [[ "$SAVE_CREDS" == "y" ]]; then
        echo "USERNAME=\"$USERNAME\"" > "$CREDENTIALS_FILE"
        echo "PASSWORD=\"$PASSWORD\"" >> "$CREDENTIALS_FILE"
        chmod 600 "$CREDENTIALS_FILE"
        success "Credentials saved to $CREDENTIALS_FILE"
    fi
fi

# Step 4: Get JWT token
info "Step 4: Obtaining JWT access token..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE_URL/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$USERNAME&password=$PASSWORD" || echo "")

if [[ -z "$TOKEN_RESPONSE" ]] || [[ "$TOKEN_RESPONSE" == *"error"* ]] || [[ "$TOKEN_RESPONSE" == *"detail"* ]]; then
    error_exit "Failed to get access token. Check your credentials."
fi

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
if [[ -z "$ACCESS_TOKEN" ]]; then
    error_exit "Could not extract access token from response"
fi
success "Access token obtained"

# Step 5: Choose update type
info "Step 5: Choosing update type..."
echo ""
echo "Update options:"
echo "1) Update only the most recent post"
echo "2) Update the last 5 posts"
echo "3) Update the last 10 posts"
echo "4) Update all posts (full sync)"
echo ""
read -p "Choose option (1-4): " UPDATE_CHOICE

case $UPDATE_CHOICE in
    1)
        UPDATE_PAYLOAD='{"most_recent_only": true}'
        UPDATE_DESC="most recent post only"
        ;;
    2)
        UPDATE_PAYLOAD='{"most_recent_only": false, "num_posts": 5}'
        UPDATE_DESC="last 5 posts"
        ;;
    3)
        UPDATE_PAYLOAD='{"most_recent_only": false, "num_posts": 10}'
        UPDATE_DESC="last 10 posts"
        ;;
    4)
        UPDATE_PAYLOAD='{"most_recent_only": false, "num_posts": null}'
        UPDATE_DESC="all posts (full sync)"
        ;;
    *)
        error_exit "Invalid choice. Please run the script again."
        ;;
esac

info "Selected: $UPDATE_DESC"

# Step 6: Perform the update
info "Step 6: Performing content update..."
warn "Note: Updates are rate-limited to 1 per hour per user"

UPDATE_RESPONSE=$(curl -s -X POST "$API_BASE_URL/rag/update" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$UPDATE_PAYLOAD" || echo "")

if [[ -z "$UPDATE_RESPONSE" ]]; then
    error_exit "No response from update endpoint"
fi

# Check if update was successful
if echo "$UPDATE_RESPONSE" | grep -q '"status":"success"'; then
    success "Content update completed successfully!"
    
    # Extract update details
    MESSAGE=$(echo "$UPDATE_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
    info "Update details: $MESSAGE"
else
    # Check for rate limiting
    if echo "$UPDATE_RESPONSE" | grep -q "rate limit\|Too many requests"; then
        error_exit "Rate limit exceeded. Please wait before trying again (1 hour limit)."
    else
        ERROR_MSG=$(echo "$UPDATE_RESPONSE" | grep -o '"detail":"[^"]*"' | cut -d'"' -f4 || echo "Unknown error")
        error_exit "Update failed: $ERROR_MSG"
    fi
fi

# Step 7: Monitor progress (optional)
info "Step 7: Checking final status..."
sleep 2  # Give the system a moment to process

FINAL_STATUS=$(curl -s -X GET "$API_BASE_URL/rag/status" \
    -H "Authorization: Bearer $ACCESS_TOKEN" || echo "")

if [[ -n "$FINAL_STATUS" ]]; then
    FINAL_COUNT=$(echo "$FINAL_STATUS" | grep -o '"document_count":[0-9]*' | cut -d':' -f2 || echo "0")
    info "Final document count: $FINAL_COUNT"
    
    if [[ -n "$CURRENT_COUNT" ]] && [[ "$FINAL_COUNT" -gt "$CURRENT_COUNT" ]]; then
        ADDED=$((FINAL_COUNT - CURRENT_COUNT))
        success "Added $ADDED new documents to the knowledge base"
    elif [[ "$FINAL_COUNT" == "$CURRENT_COUNT" ]]; then
        info "No new documents added (content was already up to date)"
    fi
fi

# Step 8: Summary
echo ""
log "${GREEN}🎉 Update Process Complete!${NC}"
log "📊 Summary:"
log "   - Update type: $UPDATE_DESC"
log "   - Log file: $LOG_FILE"
log "   - Timestamp: $(date)"

# Optional: Show recent progress
PROGRESS_RESPONSE=$(curl -s -X GET "$API_BASE_URL/rag/progress" || echo "")
if [[ -n "$PROGRESS_RESPONSE" ]] && [[ "$PROGRESS_RESPONSE" != *"error"* ]]; then
    STAGE=$(echo "$PROGRESS_RESPONSE" | grep -o '"stage":"[^"]*"' | cut -d'"' -f4)
    PROGRESS_MSG=$(echo "$PROGRESS_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
    if [[ -n "$STAGE" ]]; then
        info "Last progress: $STAGE - $PROGRESS_MSG"
    fi
fi

echo ""
info "💡 Next steps:"
info "   - Test the chatbot with new content"
info "   - Check the API docs at $API_BASE_URL/docs"
info "   - Monitor server logs for any issues"

success "All done! 🚀"
