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

### **Public Endpoints (No Authentication)**
- `GET /`: Welcome message
- `GET /rag/health`: Health check endpoint

### **Protected Endpoints (Require JWT Authentication)**
- `GET /rag/status`: Get RAG system status and document count (30/minute)
- `POST /rag/update`: Update blog content from GitHub repository (1/hour)
- `POST /rag/search`: Search blog content using semantic similarity (20/minute)
- `POST /rag/generate`: Generate AI responses using RAG with chat history (10/minute)
- `GET /rag/progress`: Get real-time progress of content updates

### **Authentication Endpoints**
- `POST /auth/register`: Register new user account
- `POST /auth/token`: Login and get JWT access token
- `GET /auth/me`: Get current user information (requires JWT)

### **Test Endpoint (Rate Limited)**
- `POST /rag/generate-test`: Generate AI responses without auth (5/minute, for testing only)

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

## API Usage Examples

### **Public Endpoints**

```bash
# Health check
curl http://<insert.host.ip.address>:8000/

# Health status
curl http://<insert.host.ip.address>:8000/rag/health
```

### **Authentication Flow**

```bash
# 1. Register new user
curl -X POST "http://<insert.host.ip.address>:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "securepassword123"}'

# 2. Login to get JWT token
curl -X POST "http://<insert.host.ip.address>:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=securepassword123"

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Use token for protected endpoints
TOKEN="your_jwt_token_here"

# Get user info
curl -X GET "http://<insert.host.ip.address>:8000/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

### **Protected RAG Endpoints**

```bash
# Check system status (requires auth)
curl -X GET "http://<insert.host.ip.address>:8000/rag/status" \
  -H "Authorization: Bearer $TOKEN"

# Update content from blog (requires auth, 1/hour limit)
curl -X POST "http://<insert.host.ip.address>:8000/rag/update" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"most_recent_only": true}'

# Search content (requires auth, 20/minute limit)
curl -X POST "http://<insert.host.ip.address>:8000/rag/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "quantum cryptography", "limit": 3}'

# Generate AI response with chat history (requires auth, 10/minute limit)
curl -X POST "http://<insert.host.ip.address>:8000/rag/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "What are recent developments in quantum computing?", "context_limit": 3}'
```

### **Test Endpoint (Limited Rate)**

```bash
# Generate AI response without auth (5/minute limit, for testing only)
curl -X POST "http://<insert.host.ip.address>:8000/rag/generate-test" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest developments in quantum cryptography?", "context_limit": 3}'
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

## Security Features

✅ **Authentication & Authorization**:
- JWT-based user authentication
- User registration and login system
- Protected endpoints with token validation
- Password hashing with bcrypt

✅ **Rate Limiting** (requests per user per timeframe):
- Content updates: 1/hour
- RAG generation: 10/minute  
- Search queries: 20/minute
- Status checks: 30/minute
- Test endpoint: 5/minute (temporary)

✅ **Network Security**:
- CORS configuration for allowed origins
- OCI Security Lists configured
- UFW firewall enabled for port 8000

## Production Status

✅ **Completed**:
- Full RAG pipeline with DeepSeek integration
- PostgreSQL database with user management
- Vector search with ChromaDB (4451+ documents)
- Authentication system with JWT tokens
- Rate limiting on all endpoints
- External access via OCI configuration
- Production-ready security middleware

🔄 **Optional Enhancements**:
- Sentry error monitoring setup
- Custom domain with HTTPS
- API key-based authentication alternative

## License

MIT 