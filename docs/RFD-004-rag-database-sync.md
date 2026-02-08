# RFD-004: RAG Database Synchronization Operations

**Request for Discussion (RFD) 004**
**Title**: RAG Database Update and Synchronization Procedures
**Status**: Implemented (Updated 2026-02-08)
**Created**: 2025-12-01
**Author**: System Architecture Team

## Summary

This RFD documents the RAG database synchronization process for ingesting blog content from the Jekyll blog repository into ChromaDB for semantic search and retrieval-augmented generation. The system fetches markdown posts from GitHub, processes them into vector embeddings, and maintains automatic deduplication to prevent duplicate content ingestion.

## Machine Constraints

**OCI Free Tier Instance**:
- **RAM**: 956MB total (~370MB available)
- **Swap**: 4GB (1.4GB typically in use)
- **CPU**: 2 vCPUs (AMD EPYC 7551)
- **Storage**: ~33GB free

**Impact on Sync Operations**:
- A full sync (all 139 posts) downloads every post from GitHub, then loads all ChromaDB metadata into memory for deduplication. On this instance, this can take over an hour due to embedding computation and memory pressure.
- On 2026-02-08, a full sync via the API endpoint ran for ~70 minutes, froze the server, and killed the uvicorn process. The sync itself completed (4,905 → 7,925 chunks), but the server was unresponsive afterward.
- **Always prefer incremental updates** (`most_recent_only: true` or `num_posts: N`) over full syncs to avoid exhausting memory and blocking the API.
- Full syncs should only be run via direct Python execution (Method 2), never through the API endpoint, and ideally during off-peak hours.

## System Architecture

### Source Repository
- **Repository**: jwt625/jwt625.github.io (GitHub public repository)
- **Content Location**: `_posts/` directory
- **File Pattern**: `YYYY-MM-DD-*.md` (Jekyll blog post format)
- **API Endpoint**: `https://api.github.com/repos/jwt625/jwt625.github.io/contents/_posts`

### Vector Database
- **Database**: ChromaDB
- **Collection Name**: blog_content
- **Storage Path**: `/home/ubuntu/chatbot/data/chromadb/`
- **Embedding Model**: Default ChromaDB embedding function
- **Current Size**: 7,925 document chunks across 139 posts (as of 2026-02-08)

### Text Processing
- **Chunk Size**: 500 characters
- **Chunk Overlap**: 100 characters
- **Metadata Preserved**: title, date, tags, categories, URL, post_id (GitHub SHA)
- **Deduplication Key**: GitHub SHA (unique identifier per post version)

## Update Mechanisms

### Method 1: API Endpoint (Authenticated)

**Endpoint**: `POST /rag/update`
**Authentication**: JWT token required
**Rate Limit**: 1 request per hour per user

**Parameters**:
```json
{
  "most_recent_only": false,
  "num_posts": null
}
```

**Options**:
- `most_recent_only: true` - Fetch only the single most recent post
- `num_posts: N` - Fetch the N most recent posts
- `num_posts: null` - Full synchronization (all posts)

**Example**:
```bash
# Authenticate
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=USERNAME&password=PASSWORD" | jq -r '.access_token')

# Full sync
curl -X POST "http://localhost:8000/rag/update" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"most_recent_only": false}'
```

**Rate Limit Notes**:
- Implemented in `app/api/rag.py:50` via SlowAPI decorator
- Limit: `@limiter.limit("1/hour")`
- Prevents abuse and excessive GitHub API calls
- Per-user tracking via JWT authentication

### Method 2: Direct Python Execution (No Rate Limit)

**Use Case**: Bulk synchronization, maintenance operations, bypassing API rate limits

**Execution**:
```bash
cd /home/ubuntu/chatbot
source venv/bin/activate

python -c "
import asyncio
from app.rag.ingestion import ContentIngester

async def main():
    ingester = ContentIngester()
    result = await ingester.update_content(
        most_recent_only=False,
        num_posts=None
    )
    print(f'Status: {result[\"status\"]}')
    print(f'Message: {result[\"message\"]}')
    if 'posts_processed' in result:
        print(f'Posts processed: {result[\"posts_processed\"]}')
    if 'chunks_added' in result:
        print(f'Chunks added: {result[\"chunks_added\"]}')

asyncio.run(main())
"
```

**Advantages**:
- No authentication required
- No rate limiting
- Direct access to ingestion functions
- Suitable for automated scripts and cron jobs

### Method 3: Interactive Update Script

**Script**: `/home/ubuntu/chatbot/scripts/update_blog_content.sh`
**Features**: Interactive prompts, authentication handling, progress monitoring

## Update Process Flow

### 1. Content Fetching Phase

**Implementation**: `app/rag/ingestion.py:58-118`

```python
async def fetch_markdown_content(
    repo_owner: str = "jwt625",
    repo_name: str = "jwt625.github.io",
    most_recent_only: bool = False,
    num_posts: int | None = None
) -> List[Dict]
```

**Steps**:
1. Query GitHub API for `_posts/` directory contents
2. Filter files matching Jekyll post pattern `YYYY-MM-DD-*.md`
3. Sort posts by date in descending order (newest first)
4. Select posts based on parameters:
   - `most_recent_only=True`: First post only
   - `num_posts=N`: First N posts
   - Neither: All posts
5. Download raw markdown content via `download_url`
6. Extract GitHub SHA for each post (used as unique identifier)

**GitHub API Rate Limits**:
- Unauthenticated: 60 requests per hour
- Authenticated: 5,000 requests per hour
- Current implementation: Unauthenticated (public repository)

### 2. Deduplication Phase

**Implementation**: `app/rag/ingestion.py:120-152`

```python
def _get_existing_post_ids(self) -> Set[str]:
    """Get set of post IDs (GitHub SHAs) that are already in the database"""
```

**Process**:
1. Query ChromaDB collection for all document metadata
2. Extract `post_id` field (GitHub SHA) from each document
3. Build set of existing post IDs
4. Compare fetched posts against existing set
5. Skip posts with matching SHA (already ingested)

**Deduplication Key**: GitHub SHA ensures version-specific deduplication. If a post is edited on GitHub, its SHA changes, triggering re-ingestion of the updated content.

### 3. Text Processing Phase

**Implementation**: `app/rag/text_processing.py`

**Jekyll Frontmatter Extraction** (`_extract_metadata:20-35`):
```python
# Extract YAML frontmatter between --- delimiters
# Parse metadata: title, date, tags, categories, etc.
# Remove frontmatter from content for chunking
```

**Text Chunking** (`chunk_text:43-121`):
```python
# Split content into overlapping chunks
# Chunk size: 500 characters
# Overlap: 100 characters
# Preserve word boundaries
# Generate unique chunk IDs: {post_sha}_chunk_{index}
```

**Metadata Preservation**:
Each chunk stores:
- `post_id`: GitHub SHA
- `post_name`: Original filename
- `title`: Post title
- `date`: Publication date
- `tags`: Post tags (comma-separated)
- `categories`: Post categories
- `url`: GitHub URL to source file
- `chunk_index`: Position within post
- `total_chunks`: Total number of chunks for post

### 4. Vector Storage Phase

**Implementation**: `app/rag/ingestion.py:154-217`

**ChromaDB Storage**:
```python
collection.add(
    ids=[f"{post_sha}_chunk_{i}" for i in range(len(chunks))],
    documents=chunks,
    metadatas=metadata_list
)
```

**Storage Location**: `/home/ubuntu/chatbot/data/chromadb/`
**Collection Name**: `blog_content`
**Persistence**: Automatic via ChromaDB persistent client

## Configuration Variables

### Environment Configuration

**File**: `app/config.py`

**Key Variables**:
```python
CHUNK_SIZE = 500          # Text chunk size in characters
CHUNK_OVERLAP = 100       # Overlap between chunks
CHROMADB_PATH = "/home/ubuntu/chatbot/data/chromadb/"
```

### Code Locations

**Core Implementation Files**:
- `app/rag/ingestion.py` - Main ingestion logic
  - `ContentIngester.fetch_markdown_content()` - GitHub fetching
  - `ContentIngester._get_existing_post_ids()` - Deduplication
  - `ContentIngester.process_and_store_content()` - Processing and storage
  - `ContentIngester.update_content()` - Main entry point

- `app/rag/text_processing.py` - Text processing utilities
  - `TextProcessor._extract_metadata()` - Frontmatter parsing
  - `TextProcessor.chunk_text()` - Text chunking with overlap
  - `TextProcessor.process_post()` - Full post processing

- `app/api/rag.py:49-69` - API endpoint
  - `POST /rag/update` - HTTP endpoint with rate limiting
  - Rate limit decorator: `@limiter.limit("1/hour")`

## Monitoring and Status

### Database Status Endpoint

**Endpoint**: `GET /rag/status`
**Rate Limit**: 30 requests per minute
**Authentication**: None required (public endpoint)

**Response**:
```json
{
  "status": "ok",
  "document_count": 4905,
  "name": "blog_content"
}
```

### Update Progress Endpoint

**Endpoint**: `GET /rag/progress`
**Authentication**: None required

**Response**:
```json
{
  "stage": "processing",
  "current": 45,
  "total": 127,
  "message": "Processing posts into chunks"
}
```

### Database File Inspection

**Check Last Modification**:
```bash
stat /home/ubuntu/chatbot/data/chromadb/chroma.sqlite3 | grep Modify
```

**Check Document Count**:
```bash
curl -s http://localhost:8000/rag/status
```

## Synchronization Best Practices

### Preferred Update Method

**For routine updates** (new posts only):
```bash
# Via API (safe, rate-limited, requires auth)
curl -X POST http://localhost:8000/rag/update \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"most_recent_only": true}'

# Or fetch last N posts
curl -X POST http://localhost:8000/rag/update \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"num_posts": 5}'
```

**For full re-sync** (use direct Python, NOT the API):
```bash
cd /home/ubuntu/chatbot
source venv/bin/activate
python -c "import asyncio; from app.rag.ingestion import ContentIngester; asyncio.run(ContentIngester().update_content())" >> /home/ubuntu/chatbot/logs/sync.log 2>&1
```
Running a full sync through the API blocks the web server for the entire duration (potentially over an hour) and can freeze the process.

### Regular Maintenance

**Recommended Schedule**:
- **Weekly**: Incremental sync (`most_recent_only: true` or `num_posts: 5`)
- **Monthly**: Full sync via direct Python execution during off-peak hours
- **Monthly**: Database integrity check — verify chunk count and check for stale SHA entries

**Automated Sync** (via cron):
```bash
# Weekly incremental sync at 2 AM Sunday (fetches last 5 posts)
0 2 * * 0 cd /home/ubuntu/chatbot && source venv/bin/activate && python -c "import asyncio; from app.rag.ingestion import ContentIngester; asyncio.run(ContentIngester().update_content(num_posts=5))" >> /home/ubuntu/chatbot/logs/sync.log 2>&1
```

### Performance Considerations

**Memory Usage**:
- ChromaDB initialization at startup loads the collection index into memory. With ~8,000 chunks, this takes ~40-50 seconds on the OCI free tier instance and adds significant memory pressure.
- A full sync downloads all posts into memory, then loads all ChromaDB metadata for deduplication. This can push memory usage close to the limit on this instance.
- Large posts: Some posts produce 100-500+ chunks (e.g., `yapping-on-ebeam-lithography.md` has 526 chunks), requiring proportionally more memory during embedding.

**Processing Time** (observed on OCI free tier):
- Full sync (139 posts, Feb 2026): ~70 minutes via API endpoint. The embedding computation for new chunks is the primary bottleneck on this CPU/memory constrained instance.
- Incremental sync (`most_recent_only: true`): A few seconds for a single post.
- ChromaDB startup: ~40-50 seconds to initialize the collection.

**WARNING**: A full sync via the API endpoint on 2026-02-08 ran for ~70 minutes and froze the uvicorn process. The sync completed but the server became unresponsive and required a manual restart. **Always prefer incremental syncs via the API. Run full syncs only via direct Python execution (Method 2) during off-peak hours.**

## Error Handling

### Common Issues

**GitHub API Rate Limiting**:
- Error: HTTP 403 with rate limit message
- Solution: Wait for rate limit reset or use authenticated requests
- Prevention: Space out update requests, use cron scheduling

**Network Failures**:
- Symptom: Connection timeout, incomplete fetches
- Recovery: Retry mechanism with exponential backoff
- Automatic: Built into httpx client

**Memory Exhaustion**:
- Symptom: Process killed, ChromaDB write failures
- Prevention: Process posts in batches for very large updates
- Monitoring: Check available memory before large operations

**Database Lock Issues**:
- Symptom: ChromaDB write failures, timeout errors
- Solution: Ensure only one update process runs at a time
- Prevention: Use file-based locking for concurrent operations

### Logging

**Log Locations**:
- Application logs: Standard output (captured by systemd/screen)
- Update logs: `/home/ubuntu/chatbot/logs/update_*.log` (from script)
- API request logs: Database table `api_request_logs`

**Debug Mode**:
```python
# Enable debug logging in app/rag/ingestion.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Success Criteria

**Successful Synchronization Indicators**:
1. Status endpoint returns increased `document_count`
2. ChromaDB database file timestamp updated
3. No error messages in logs
4. New posts searchable via `/rag/search` endpoint
5. Deduplication working (existing posts skipped)

**Verification Query**:
```bash
# Check most recent post
curl -s -X POST "http://localhost:8000/rag/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "recent", "limit": 1}' | jq
```

## Maintenance Procedures

### Database Cleanup

**Remove All Embeddings** (destructive):
```bash
# Stop service first
rm -rf /home/ubuntu/chatbot/data/chromadb/*
# Restart service - collection will be recreated
```

**Re-sync from Scratch**:
```bash
# After cleanup, run full sync
cd /home/ubuntu/chatbot
source venv/bin/activate
python -c "import asyncio; from app.rag.ingestion import ContentIngester; asyncio.run(ContentIngester().update_content())"
```

### Database Optimization

**ChromaDB Performance**:
- Automatic indexing on insertion
- No manual optimization required
- Storage automatically compacted

**Monitoring Storage Usage**:
```bash
du -sh /home/ubuntu/chatbot/data/chromadb/
```

## Security Considerations

**API Access Control**:
- Update endpoint requires JWT authentication
- Rate limiting prevents abuse
- User-level tracking for audit trails

**GitHub Repository Access**:
- Public repository: No authentication needed
- Private repository: Would require GitHub token in environment variable

**Data Privacy**:
- Blog posts are public content
- No sensitive data stored in embeddings
- Metadata includes only public post information

## Known Issues

### Stale Chunk Accumulation
The deduplication mechanism uses GitHub SHA as the key. When a post is edited on GitHub, its SHA changes. The ingester treats the edited post as new and adds fresh chunks, but **does not remove the old chunks** (which have IDs based on the old SHA). Over time this causes the chunk count to grow beyond what's expected for the number of posts.

**Impact**: The database grew from 4,905 chunks (Dec 2025) to 7,925 chunks (Feb 2026) despite only 12 new posts being added. The excess growth is from re-ingested edited posts.

**Mitigation**: Periodically do a full database cleanup and re-sync from scratch (see Maintenance Procedures below). A proper fix would require the ingester to delete old chunks when a post's SHA changes.

### Full Sync Blocks/Crashes the API Server
Running a full sync through the `/rag/update` API endpoint blocks the uvicorn event loop for the entire duration of the sync. On the memory-constrained OCI instance, this has caused the server to become unresponsive and eventually crash. Always use direct Python execution for full syncs.

## Future Enhancements

**Potential Improvements**:
1. Stale chunk cleanup — delete old chunks when a post's SHA changes
2. Incremental updates based on last sync timestamp
3. Webhook-based updates (GitHub webhook integration)
4. Run full sync in a background worker process instead of the main API process
5. Differential updates (only re-process changed posts)
6. Multi-repository support
7. Custom embedding models

## Historical Context

**Previous Synchronization**:
- Last update before December 2025: July 7, 2025
- Gap: Nearly 5 months of content not indexed
- Posts missing: July 7 - November 23, 2025

**December 2025 Sync**:
- Total posts in repository: 127
- Total documents after sync: 4,905 chunks
- Last sync: 2025-12-01 08:00 UTC

**February 2026 Sync** (2026-02-08):
- Full sync ran via API endpoint, took ~70 minutes, froze the server
- Sync completed successfully before the server became unresponsive
- Total posts in repository: 139
- Total documents after sync: 7,925 chunks
- Chunk growth includes both new posts and stale chunks from edited posts
- Server required manual restart (tmux session `chatbot`)
- ChromaDB startup now takes ~40-50 seconds due to larger collection

## Conclusion

The RAG database synchronization system provides reliable ingestion of blog content from GitHub into ChromaDB for semantic search. The deduplication mechanism prevents exact-SHA duplicate ingestion, but does not clean up stale chunks from edited posts — this requires periodic manual cleanup. On the resource-constrained OCI free tier instance (956MB RAM), **incremental syncs should always be preferred** over full syncs, and full syncs should never be run through the API endpoint.
