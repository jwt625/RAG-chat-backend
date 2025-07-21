# RFD-000: API Activity Logging Implementation

**Request for Discussion (RFD) 000**  
**Title**: Minimal API Activity Logging for Resource-Constrained Environment  
**Status**: Draft  
**Created**: 2025-07-21  
**Author**: System Architecture Team  

## Summary

This RFD proposes implementing a lightweight API activity logging system for the RAG chatbot backend that tracks user interactions, system performance, and security events while operating within the constraints of a free OCI instance with limited compute, memory, and storage.

## Motivation

Currently, the system lacks:
- API request/response logging
- User activity tracking
- Authentication audit trails
- Performance monitoring data
- Security event logging

This creates operational blind spots and makes debugging, security monitoring, and usage analysis impossible.

## Design Decision: PostgreSQL vs ChromaDB

**Decision: Use PostgreSQL**

Rationale:
- Already in use for authentication and chat storage
- No additional memory overhead from another database
- Better suited for structured log data with timestamps
- Supports efficient time-based queries and data rotation
- Native support for indexes on timestamp columns
- Can leverage existing connection pool

ChromaDB is optimized for vector similarity search, not time-series log data.

## Proposed Architecture

### 1. Database Schema (PostgreSQL)

```sql
-- Core activity log table (minimal design)
CREATE TABLE api_activity_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER REFERENCES users(id),
    method VARCHAR(10),
    endpoint VARCHAR(100),
    status_code SMALLINT,
    response_time_ms INTEGER,
    ip_address INET,
    user_agent VARCHAR(200),
    error_message TEXT,
    -- Indexes for performance
    INDEX idx_timestamp (timestamp),
    INDEX idx_user_id (user_id),
    INDEX idx_endpoint (endpoint)
);

-- Separate table for authentication events (security critical)
CREATE TABLE auth_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(50),
    event_type VARCHAR(20), -- 'login_success', 'login_failure', 'register', 'token_refresh'
    ip_address INET,
    user_agent VARCHAR(200),
    failure_reason VARCHAR(100),
    INDEX idx_timestamp (timestamp),
    INDEX idx_username (username)
);

-- Aggregated metrics table (for dashboard/monitoring)
CREATE TABLE api_metrics_hourly (
    hour TIMESTAMP PRIMARY KEY,
    endpoint VARCHAR(100),
    total_requests INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    avg_response_time_ms INTEGER,
    unique_users INTEGER DEFAULT 0,
    INDEX idx_hour_endpoint (hour, endpoint)
);
```

### 2. Storage Management Strategy

To handle limited storage:
- **Retention Policy**: 30 days for detailed logs, 90 days for aggregated metrics
- **Log Rotation**: Daily cleanup job to delete old records
- **Aggregation**: Hourly rollup of metrics to reduce storage
- **Selective Logging**: Only log non-GET requests and errors for GET requests
- **Size Limits**: Cap user_agent and error_message fields

### 3. Implementation Phases

## Phase 1: Core Infrastructure (Week 1)

**Goal**: Set up basic logging middleware and database tables

**TODO List**:
- [ ] Create Alembic migration for activity log tables
- [ ] Implement FastAPI middleware for request/response logging
- [ ] Create data models for log entries
- [ ] Add database repository functions for log insertion
- [ ] Implement async background task for log writing (non-blocking)
- [ ] Add configuration settings for logging levels
- [ ] Create unit tests for logging components

**Deliverables**:
- `alembic/versions/xxx_add_activity_logging.py`
- `app/middleware/activity_logger.py`
- `app/models/activity_log.py`
- `app/repositories/activity_log_repo.py`

## Phase 2: Authentication Logging (Week 2)

**Goal**: Track all authentication-related events

**TODO List**:
- [ ] Modify auth endpoints to log login attempts
- [ ] Log successful and failed authentication
- [ ] Track user registration events
- [ ] Add JWT token validation logging
- [ ] Implement brute-force detection queries
- [ ] Create auth event dashboard queries
- [ ] Add tests for auth logging

**Deliverables**:
- Updated `app/api/auth.py` with logging
- `app/services/auth_monitor.py`
- Auth monitoring SQL queries

## Phase 3: Performance Monitoring (Week 3)

**Goal**: Track API performance and resource usage

**TODO List**:
- [ ] Add response time tracking to middleware
- [ ] Implement endpoint performance aggregation
- [ ] Create hourly metrics aggregation job
- [ ] Add slow query detection and logging
- [ ] Monitor ChromaDB query performance
- [ ] Track DeepSeek API latency
- [ ] Create performance dashboard queries

**Deliverables**:
- `app/tasks/metrics_aggregator.py`
- `app/monitoring/performance.py`
- Performance monitoring queries

## Phase 4: Storage Management (Week 4)

**Goal**: Implement log rotation and cleanup

**TODO List**:
- [ ] Create daily cleanup job for old logs
- [ ] Implement log archival process (optional)
- [ ] Add storage usage monitoring
- [ ] Create alerts for high storage usage
- [ ] Implement log compression (if needed)
- [ ] Add configuration for retention policies
- [ ] Test cleanup processes

**Deliverables**:
- `app/tasks/log_cleanup.py`
- `app/config/retention_policy.py`
- Cleanup job scheduling

## Phase 5: Observability Dashboard (Week 5)

**Goal**: Create simple monitoring endpoints

**TODO List**:
- [ ] Create `/admin/metrics` endpoint (protected)
- [ ] Add endpoint for recent activity logs
- [ ] Implement error rate monitoring endpoint
- [ ] Create user activity summary endpoint
- [ ] Add system health aggregation endpoint
- [ ] Document all monitoring endpoints
- [ ] Create simple CLI monitoring tool

**Deliverables**:
- `app/api/admin/monitoring.py`
- `scripts/monitor_api.py`
- Monitoring documentation

## Implementation Details

### 1. Minimal Logging Middleware

```python
# app/middleware/activity_logger.py
from fastapi import Request
import time
import asyncio
from app.repositories.activity_log_repo import create_activity_log

async def activity_logging_middleware(request: Request, call_next):
    # Skip logging for health checks and static files
    if request.url.path in ["/", "/health", "/docs"]:
        return await call_next(request)
    
    start_time = time.time()
    response = await call_next(request)
    process_time = int((time.time() - start_time) * 1000)
    
    # Log asynchronously to avoid blocking
    asyncio.create_task(log_activity(
        request, response.status_code, process_time
    ))
    
    return response
```

### 2. Resource-Conscious Design

- Use database connection pooling efficiently
- Batch insert logs when possible
- Implement circuit breaker for logging failures
- Graceful degradation if logging fails
- Minimal memory footprint for log objects

### 3. Security Considerations

- Never log sensitive data (passwords, tokens)
- Hash/mask IP addresses for privacy (optional)
- Implement rate limiting on monitoring endpoints
- Secure admin endpoints with separate authentication

## Monitoring Queries Examples

```sql
-- Failed login attempts in last hour
SELECT COUNT(*), username, ip_address 
FROM auth_logs 
WHERE event_type = 'login_failure' 
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY username, ip_address
HAVING COUNT(*) > 3;

-- API performance by endpoint (last 24h)
SELECT endpoint, 
       COUNT(*) as requests,
       AVG(response_time_ms) as avg_time,
       MAX(response_time_ms) as max_time,
       SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) as errors
FROM api_activity_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY endpoint
ORDER BY requests DESC;

-- Storage usage estimation
SELECT 
  pg_size_pretty(pg_relation_size('api_activity_logs')) as log_size,
  COUNT(*) as total_records,
  MIN(timestamp) as oldest_record
FROM api_activity_logs;
```

## Resource Impact Analysis

**Memory Impact**: 
- ~50KB additional memory for middleware
- Async logging prevents blocking
- Reuses existing database connections

**Storage Impact** (estimated):
- ~200 bytes per API request log
- At 10,000 requests/day = 2MB/day
- 30-day retention = 60MB for activity logs
- Hourly aggregation reduces long-term storage

**CPU Impact**:
- Minimal - async logging in background
- Batch processing for aggregation
- Indexed queries for fast retrieval

## Alternative Approaches Considered

1. **File-based logging**: Rejected due to difficult querying and rotation
2. **External service (CloudWatch, etc.)**: Rejected due to cost
3. **Redis**: Rejected due to memory constraints
4. **SQLite**: Rejected due to concurrent write limitations

## Success Criteria

1. All API requests are logged within 50ms overhead
2. Storage usage stays under 100MB for logging
3. Can query logs for security incidents within seconds
4. System remains stable under load with logging enabled
5. Easy to disable logging in case of resource issues

## Rollback Plan

If logging impacts performance:
1. Disable middleware via environment variable
2. Truncate log tables to free space
3. Implement sampling (log only X% of requests)
4. Move to file-based logging temporarily

## Future Enhancements

- Export logs to external storage (S3)
- Implement log sampling for high-traffic endpoints
- Add distributed tracing support
- Create Grafana dashboards
- Implement anomaly detection

## Conclusion

This minimal approach provides essential observability while respecting resource constraints. The phased implementation allows for gradual rollout with monitoring at each step to ensure system stability.