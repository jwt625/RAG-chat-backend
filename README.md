# RAG Chat Backend

A FastAPI-based backend service for implementing RAG (Retrieval Augmented Generation) capabilities for a Jekyll blog. The system ingests blog content from GitHub, processes it into vector embeddings, and provides AI-powered search and response generation using DeepSeek LLM.

## Features

- **RAG Pipeline**: Complete retrieval-augmented generation workflow
- **FastAPI REST API**: Modern async web framework with automatic OpenAPI docs
- **ChromaDB Vector Storage**: Semantic search with embeddings
- **PostgreSQL**: User authentication and conversation history
- **DeepSeek LLM Integration**: OpenAI-compatible API for response generation
- **Comprehensive API Logging**: Complete request/response logging with enhanced RAG endpoint tracking
- **Production Ready**: Security middleware, rate limiting, monitoring

## Project Structure

```
/chatbot/
├── app/
│   ├── api/          # API endpoints
│   ├── rag/          # RAG implementation
│   ├── middleware/   # Logging and security middleware
│   └── utils/        # Utility functions
├── data/
│   └── chromadb/     # Vector database storage
├── alembic/          # Database migrations
├── docs/             # RFD documentation
├── logs/             # Application logs
├── scripts/          # Utility scripts
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

5. Run database migrations:
```bash
source venv/bin/activate
alembic upgrade head
```

6. Start the server:
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

# Logging (optional)
LOGGING_ENABLED=true
LOG_RETENTION_DAYS=30
```

## Database Schema

The application uses PostgreSQL with the following main tables:

**Core Tables**:
- `users` - User accounts and authentication
- `chats` - Chat sessions for conversation history
- `messages` - Individual messages in chat sessions

**Logging Tables**:
- `api_request_logs` - Comprehensive API request logging
  - All request/response metadata
  - Enhanced RAG endpoint data (queries, context, responses)
  - Performance metrics and error tracking
- `daily_metrics` - Aggregated daily statistics
- `alembic_version` - Database migration tracking

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

**RAG & API Testing**:
- `scripts/test_rag_demo.py`: Interactive demo of the complete RAG workflow
- `scripts/test_logging.py`: Test comprehensive API logging functionality
- `tests/test_deepseek_api.py`: DeepSeek API integration tests
- `tests/test_full_rag_workflow.py`: Comprehensive RAG workflow tests

**Monitoring & Analysis**:
- `scripts/check_logs.py`: Analyze API request logs and generate reports
- `scripts/sql_queries.sql`: Collection of useful SQL queries for log analysis

## Documentation

**Request for Discussion (RFD) Documents**:
- `docs/RFD-000-api-activity-logging.md`: Original lightweight logging proposal
- `docs/RFD-001-HTTPS-certificate.md`: HTTPS certificate implementation
- `docs/RFD-002-mobile-cors-fix.md`: Mobile CORS compatibility fixes
- `docs/RFD-003-comprehensive-api-logging.md`: ✅ Comprehensive logging implementation

## API Logging & Monitoring

✅ **Comprehensive Request Logging**:
- Every API request logged to PostgreSQL database
- Enhanced logging for RAG generate endpoints
- Request/response timing and size tracking
- User activity and IP address logging
- Error tracking and analysis

✅ **RAG Endpoint Analytics**:
- Full query text capture
- Context chunks analysis (count, sources, distances)
- Response length and quality metrics
- Chat session correlation
- Performance monitoring

✅ **Monitoring Tools**:
- `scripts/check_logs.py` - Python log analysis tool
- `scripts/sql_queries.sql` - SQL queries for manual inspection
- `scripts/test_logging.py` - Logging functionality tests

### Check API Logs

**Python Analysis Tool**:
```bash
source venv/bin/activate
python scripts/check_logs.py
```

**SQL Database Queries**:
```bash
# Recent requests
sudo -u postgres psql -d chatbot_db -c "SELECT timestamp, method, path, status_code FROM api_request_logs ORDER BY timestamp DESC LIMIT 10;"

# Generate endpoint stats
sudo -u postgres psql -d chatbot_db -c "SELECT COUNT(*), AVG(response_time_ms) FROM api_request_logs WHERE event_type = 'rag_generate';"
```

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