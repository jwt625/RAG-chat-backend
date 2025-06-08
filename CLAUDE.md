# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval Augmented Generation) chatbot backend built with FastAPI that serves the Jekyll blog `jwt625.github.io`. The system ingests blog content from GitHub, processes it into vector embeddings using ChromaDB, and provides AI-powered search and response generation using DeepSeek LLM.

## Development Commands

**Start the RAG service:**
```bash
cd /home/ubuntu/chatbot && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Authentication Flow:**
```bash
# Register user
curl -X POST "http://localhost:8000/auth/register" -H "Content-Type: application/json" -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'

# Login to get JWT token  
curl -X POST "http://localhost:8000/auth/token" -H "Content-Type: application/x-www-form-urlencoded" -d "username=testuser&password=password123"

# Set token for authenticated requests
TOKEN="your_jwt_token_here"
```

**Protected RAG Operations (require JWT token):**
```bash
# Update RAG database (1/hour rate limit)
curl -X POST http://localhost:8000/rag/update -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"most_recent_only": true}'

# Search content (20/minute rate limit)
curl -X POST http://localhost:8000/rag/search -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"query": "quantum computing", "limit": 3}'

# Generate RAG response with chat history (10/minute rate limit)
curl -X POST "http://localhost:8000/rag/generate" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"query": "What are recent developments in quantum cryptography?", "context_limit": 3}'
```

**Public/Test Endpoints:**
```bash
# Health check (no auth)
curl http://localhost:8000/

# Test RAG generation (5/minute rate limit, no auth)
curl -X POST "http://localhost:8000/rag/generate-test" -H "Content-Type: application/json" -d '{"query": "What are the latest developments in quantum cryptography?", "context_limit": 3}'
```

**Run tests:**
```bash
pytest
```

**Code formatting and type checking:**
```bash
black .
mypy .
```

**Setup virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Architecture

### Core Components
- **FastAPI Backend** (`app/main.py`) - Main web server with CORS middleware
- **RAG System** (`app/rag/`) - Content ingestion and retrieval logic
- **Database Layer** (`app/database.py`, `app/models.py`) - PostgreSQL with SQLAlchemy ORM
- **Authentication** (`app/security.py`) - JWT-based user authentication
- **Vector Storage** - ChromaDB for semantic search embeddings

### Data Flow
1. **Content Ingestion**: Fetches Jekyll posts from GitHub `_posts/` directory
2. **Text Processing**: Extracts frontmatter and chunks content (500 chars, 100 overlap)
3. **Vector Embedding**: Stores chunks in ChromaDB with metadata
4. **Query Processing**: Searches embeddings and generates responses via DeepSeek API
5. **Conversation Storage**: Persists chat history in PostgreSQL

### Database Schema
- `User` - Authentication and user management
- `Chat` - Chat sessions linked to users  
- `Message` - Individual messages with RAG context tracking

## Key Configuration

**Environment Variables:**
- Database connection settings for PostgreSQL
- `DEEPSEEK_API_KEY` for LLM integration
- `SECRET_KEY` for JWT authentication
- `ALLOWED_ORIGINS` (currently `https://jwt625.github.io`)
- Text processing: `CHUNK_SIZE=500`, `CHUNK_OVERLAP=100`

**Vector Database:**
- ChromaDB collection: `blog_content`
- Persistent storage in `/data/chromadb/`

## API Endpoints

- `POST /rag/update` - Sync blog content from GitHub
- `POST /rag/search` - Semantic search blog posts
- `POST /rag/generate` - Generate AI responses with RAG context
- `GET /rag/status` - System status and metrics
- `GET /rag/progress` - Real-time update progress

## Testing

Tests use PyTest with temporary ChromaDB instances (`/tmp/test_chroma`). The test suite covers:
- API endpoint integration
- RAG functionality (ingestion, search, generation)
- Text processing and chunking
- Database operations

## Recent Security & Production Updates

### **Authentication System** (Added December 2024)
- **JWT-based authentication**: User registration, login, token management
- **Database integration**: User accounts stored in PostgreSQL with bcrypt password hashing
- **Protected endpoints**: All RAG operations now require valid JWT tokens
- **Files added**: `app/api/auth.py` for authentication endpoints

### **Rate Limiting** (Enhanced December 2024)  
All endpoints now have rate limiting via SlowAPI:
- Content updates: 1/hour (prevents abuse)
- RAG generation: 10/minute 
- Search queries: 20/minute
- Status checks: 30/minute
- Test endpoint: 5/minute (temporary for testing)

### **Security Enhancements**
- **CORS configuration**: Restricted to specific domains for production
- **Network security**: OCI Security Lists configured for external access
- **Firewall setup**: UFW enabled for port 8000
- **Token validation**: OAuth2PasswordBearer scheme implemented

### **External Access Configuration**
- **OCI networking**: Security Lists, Route Tables, Internet Gateway configured
- **Public IP access**: Server accessible at `http://<TBA>:8000`
- **Health endpoints**: Public health check available at `/` and `/rag/health`

### **Code Structure Changes**
- **Authentication router**: Added to `app/main.py` 
- **Internal functions**: `_internal_search()` to avoid auth conflicts
- **Rate limiting decorators**: Added to all endpoints in `app/api/rag.py`
- **Request parameters**: Added to support SlowAPI rate limiting

### **Production Dependencies Added**
```txt
slowapi==0.1.9          # Rate limiting
sentry-sdk==2.29.1       # Error monitoring  
psutil==7.0.0           # System monitoring
PyJWT==2.10.1           # JWT authentication
email-validator==2.2.0  # Email validation
```

### **Database Schema**
- **User table**: Authentication and user management
- **Chat table**: Conversation sessions per user
- **Message table**: Chat history with RAG context tracking

## Current Status
- ✅ **Fully functional**: External access, authentication, rate limiting
- ✅ **Production ready**: Security, monitoring, error handling
- 🔄 **Optional**: Sentry DSN, custom domain, HTTPS setup