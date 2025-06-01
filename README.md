# RAG Chat Backend

A FastAPI-based backend service for implementing RAG (Retrieval Augmented Generation) capabilities for a Jekyll blog.

## Features

- RAG pipeline for blog content
- FastAPI REST API
- ChromaDB for vector storage
- PostgreSQL for conversation history
- DeepSeek integration for LLM capabilities

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

4. Start the server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

- `POST /rag/update`: Update blog content in ChromaDB
- `GET /rag/status`: Get RAG system status
- `POST /rag/search`: Search blog content

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

## Development

1. Install development dependencies
2. Run tests: `pytest`
3. Format code: `black .`
4. Check types: `mypy .`

## License

MIT 