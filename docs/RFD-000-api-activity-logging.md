# RFD-000: API Activity Logging Implementation

**Request for Discussion (RFD) 000**  
**Title**: Minimal API Activity Logging for Resource-Constrained Environment  
**Status**: Draft (Revised)  
**Created**: 2025-07-21  
**Author**: System Architecture Team  

## Summary

This RFD proposes implementing an ultra-lightweight API activity logging system for the RAG chatbot backend that tracks critical security events and errors while operating within severe memory constraints of a free OCI instance (956MB RAM with only 402MB available).

## System Constraints

**Actual Machine Specifications:**
- **RAM**: 956MB total (402MB available, 1.4GB swap already in use)
- **CPU**: 2 vCPUs (AMD EPYC 7551)
- **Storage**: 33GB free (of 45GB total)
- **Current Usage**: PostgreSQL (8.8MB), ChromaDB (213MB)

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

## Revised Architecture (Memory-Optimized)

### 1. Hybrid Logging Strategy

Given severe memory constraints, we'll use a **hybrid approach**:
- **PostgreSQL**: Only for critical security events (auth failures, errors)
- **File-based**: For general API activity (rotating daily)
- **In-memory**: Minimal metrics buffer (last hour only)

### 2. Database Schema (PostgreSQL - Security Events Only)

```sql
-- Minimal auth events table (security critical only)
CREATE TABLE auth_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(50),
    event_type VARCHAR(20), -- 'login_failure', 'register', 'suspicious_activity'
    ip_address INET,
    details VARCHAR(200), -- Truncated details
    INDEX idx_timestamp (timestamp),
    INDEX idx_username_type (username, event_type)
);

-- Daily aggregated metrics (compressed storage)
CREATE TABLE metrics_daily (
    date DATE PRIMARY KEY,
    metrics JSONB -- Compressed JSON with endpoint stats
);
```

### 3. File-Based Activity Logging

```python
# Use Python's built-in logging with rotation
# Logs to: /home/ubuntu/chatbot/logs/api/
# Format: api-2024-07-21.log (max 10MB, keep 7 days)
```

### 4. Memory-Conscious Storage Strategy

**Revised Retention Policy**:
- **Database**: 7 days for auth events only
- **File logs**: 7 days rolling (10MB max per file)
- **Metrics**: Daily aggregation only (30 days)
- **Memory buffer**: Last 1 hour only (evicted on rotation)

**Selective Logging Rules**:
- Auth failures: Always log to database
- 5xx errors: Always log to database
- 4xx errors: Sample 10% to files
- Successful requests: Sample 1% to files only
- Health checks: Never log

### 5. Revised Implementation Phases

## Phase 1: Security Event Logging (Week 1) - START HERE

**Goal**: Log only critical security events to minimize memory impact

**TODO List**:
- [ ] Create minimal Alembic migration for auth_events table only
- [ ] Update auth endpoints to log failures only
- [ ] Implement memory-efficient batch writing (buffer 10 events max)
- [ ] Add circuit breaker to disable logging if memory < 100MB
- [ ] Configure Python file logger with rotation
- [ ] Test memory impact with load testing
- [ ] Add emergency kill switch environment variable

**Deliverables**:
- `alembic/versions/xxx_add_auth_events.py`
- `app/middleware/security_logger.py` (lightweight)
- `app/utils/memory_monitor.py`

## Phase 2: File-Based Activity Logging (Week 2)

**Goal**: Add lightweight file logging for non-critical events

**TODO List**:
- [ ] Set up rotating file handler (10MB max, 7 files)
- [ ] Implement sampling logic (1% success, 10% client errors)
- [ ] Create structured log format (JSON lines)
- [ ] Add async file writing to prevent blocking
- [ ] Test file I/O impact on performance
- [ ] Create log parser script for analysis

**Deliverables**:
- `app/logging/file_logger.py`
- `scripts/parse_logs.py`

## Phase 3: Minimal Metrics Buffer (Week 3)

**Goal**: In-memory metrics with automatic eviction

**TODO List**:
- [ ] Implement fixed-size circular buffer (1000 events max)
- [ ] Create metrics aggregation in memory
- [ ] Add automatic eviction when memory < 150MB
- [ ] Implement metrics snapshot endpoint
- [ ] Add memory usage to health check
- [ ] Test memory footprint

**Deliverables**:
- `app/utils/metrics_buffer.py`
- Updated health check endpoint

## Phase 4: Daily Aggregation (Week 4)

**Goal**: Compress and store daily metrics

**TODO List**:
- [ ] Create daily aggregation job (runs at 2 AM)
- [ ] Compress metrics to JSONB format
- [ ] Implement file log parsing and summarization
- [ ] Clean up old auth events (> 7 days)
- [ ] Add storage monitoring alerts
- [ ] Create backup script for metrics

**Deliverables**:
- `app/tasks/daily_aggregation.py`
- `scripts/backup_metrics.sh`

## Implementation Details

### 1. Ultra-Minimal Security Logger

```python
# app/middleware/security_logger.py
import psutil
from collections import deque
from app.config import LOGGING_ENABLED

# Global in-memory buffer (max 10 events)
SECURITY_BUFFER = deque(maxlen=10)

async def security_logging_middleware(request: Request, call_next):
    # Emergency kill switch
    if not LOGGING_ENABLED:
        return await call_next(request)
    
    # Check memory before logging
    if psutil.virtual_memory().available < 100 * 1024 * 1024:  # 100MB
        return await call_next(request)
    
    response = await call_next(request)
    
    # Only log security-relevant events
    if response.status_code == 401 or \
       (request.url.path.startswith("/auth") and response.status_code >= 400):
        SECURITY_BUFFER.append({
            "timestamp": datetime.utcnow(),
            "path": request.url.path[:50],  # Truncate
            "status": response.status_code,
            "ip": request.client.host
        })
    
    return response

# Batch write every 60 seconds
async def flush_security_buffer():
    if SECURITY_BUFFER and psutil.virtual_memory().available > 150 * 1024 * 1024:
        # Write to DB and clear buffer
        pass
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

## Revised Resource Impact Analysis

**Memory Impact** (Critical Constraint): 
- ~10KB for security event buffer (10 events max)
- ~50KB for file logging buffer
- Automatic disabling if available RAM < 100MB
- No additional database connections (reuse existing pool)

**Storage Impact** (Manageable):
- Database: ~100 bytes per security event × 100 events/day = 10KB/day
- File logs: 10MB max × 7 files = 70MB total
- Daily metrics: ~5KB per day × 30 days = 150KB
- **Total**: < 100MB for all logging

**CPU Impact** (Minimal):
- File I/O: Async with OS buffering
- Database writes: Batched every 60 seconds
- Sampling reduces processing by 99%

## Alternative Approaches Considered

1. **Full PostgreSQL logging**: Rejected due to memory overhead
2. **External service (CloudWatch, etc.)**: Rejected due to cost
3. **Redis**: Rejected due to severe memory constraints
4. **SQLite**: Considered but rejected (still requires memory)
5. **No logging**: Considered but rejected (security risk)

## Success Criteria

1. Security events logged with < 10ms overhead
2. Memory usage increase < 100KB
3. Storage usage < 100MB total
4. System remains stable when memory < 200MB available
5. Zero impact on swap usage
6. Automatic disabling when resources critical

## Emergency Procedures

If system becomes unstable:
1. **Immediate**: Set `LOGGING_ENABLED=false` (kills all logging)
2. **Quick fix**: Reduce buffer size to 5 events
3. **Storage full**: Delete file logs older than 1 day
4. **Memory critical**: System auto-disables at 100MB
5. **Database issues**: Fall back to file-only logging

## Future Enhancements (When Resources Allow)

- Upgrade to larger instance for full logging
- External log aggregation service
- Prometheus metrics (requires ~100MB RAM)
- Full request/response logging
- Real-time alerting

## Conclusion

This ultra-lightweight approach provides critical security logging while respecting severe memory constraints (956MB total, 402MB available). The hybrid strategy using minimal database logging for security events and sampled file logging for general activity ensures the system remains stable. The implementation prioritizes system stability over comprehensive logging, with automatic safeguards to prevent resource exhaustion.