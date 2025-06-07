# RAG Chat Backend

A FastAPI-based backend service for implementing RAG (Retrieval Augmented Generation) capabilities for a Jekyll blog. The system ingests blog content from GitHub, processes it into vector embeddings, and provides AI-powered search and response generation using DeepSeek LLM.

## Features

- **RAG Pipeline**: Complete retrieval-augmented generation workflow
- **FastAPI REST API**: Modern async web framework with automatic OpenAPI docs
- **ChromaDB Vector Storage**: Semantic search with embeddings
- **PostgreSQL**: User authentication and conversation history
- **DeepSeek LLM Integration**: OpenAI-compatible API for response generation
- **Production Ready**: Security middleware, rate limiting, monitoring

## Project Structure

```
/chatbot/
├── app/
│   ├── api/          # API endpoints
│   ├── rag/          # RAG implementation
│   └── utils/        # Utility functions
├── data/
│   └── chromadb/     # Vector database storage
├── alembic/          # Database migrations
└── tests/            # Test cases
```

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Set up PostgreSQL database:
```bash
sudo -u postgres createuser -d -r -s chatbot
sudo -u postgres psql -c "ALTER USER chatbot PASSWORD 'dev_password_123';"
sudo -u postgres createdb -O chatbot chatbot_db
```

5. Start the server:
```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /`: Welcome message
- `GET /rag/status`: Get RAG system status and document count
- `POST /rag/update`: Update blog content from GitHub repository
- `POST /rag/search`: Search blog content using semantic similarity
- `POST /rag/generate`: Generate AI responses using RAG (requires authentication)
- `POST /rag/generate-test`: Generate AI responses using RAG (no authentication, for testing)
- `GET /rag/progress`: Get real-time progress of content updates

## Environment Variables

Required environment variables in `.env`:

```env
# Database
POSTGRES_USER=chatbot
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chatbot_db

# Security
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Keys
DEEPSEEK_API_KEY=your_deepseek_api_key

# CORS
CORS_ORIGINS=["https://jwt625.github.io"]
```

## Quick Test

Test the RAG workflow:

```bash
# Check system status
curl -s http://localhost:8000/rag/status

# Update content from blog
curl -X POST http://localhost:8000/rag/update -H "Content-Type: application/json" -d '{"most_recent_only": true}'

# Search content
curl -X POST http://localhost:8000/rag/search -H "Content-Type: application/json" -d '{"query": "quantum cryptography", "limit": 3}'

# Generate AI response (test endpoint)
curl -X POST http://localhost:8000/rag/generate-test -H "Content-Type: application/json" -d '{"query": "What are the latest developments in quantum cryptography?", "context_limit": 3}'
```

## Development

1. Install development dependencies
2. Run tests: `pytest` 
3. Format code: `black .`
4. Check types: `mypy .`

## Test Scripts

- `scripts/test_rag_demo.py`: Interactive demo of the complete RAG workflow
- `tests/test_deepseek_api.py`: DeepSeek API integration tests
- `tests/test_full_rag_workflow.py`: Comprehensive RAG workflow tests

## Production Status

✅ **Core Features Complete**:
- RAG pipeline with DeepSeek integration
- PostgreSQL database setup
- Vector search with ChromaDB
- Production dependencies installed

🔄 **Remaining Production TODOs**:
- Sentry DSN configuration
- Trusted host domains setup  
- API key validation implementation

## License

MIT 