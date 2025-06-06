# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval Augmented Generation) chatbot backend built with FastAPI that serves the Jekyll blog `jwt625.github.io`. The system ingests blog content from GitHub, processes it into vector embeddings using ChromaDB, and provides AI-powered search and response generation using DeepSeek LLM.

## Development Commands

**Start the RAG service:**
```bash
cd /home/ubuntu/chatbot && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Run tests:**
```bash
pytest
```

**Update RAG database:**
```bash
curl -X POST http://localhost:8000/rag/update -H "Content-Type: application/json" -d '{"most_recent_only": true}'
```

**Query RAG database:**
```bash
curl -X POST http://localhost:8000/rag/search -H "Content-Type: application/json" -d '{"query": "What was discussed about quantum computing?", "limit": 3}'
```

**Generate RAG response:**
```bash
curl -X POST "http://localhost:8000/rag/generate" -H "Content-Type: application/json" -d '{"query": "What are the latest developments in quantum cryptography?", "context_limit": 3}'
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

## Production Features

The codebase includes production-ready features:
- Sentry error monitoring integration
- Rate limiting with SlowAPI
- Rotating log files in `/logs/`
- Resource monitoring utilities
- GZip compression and trusted host middleware