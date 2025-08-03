-- Useful SQL queries for checking API request logs

-- 1. Total number of logged requests
SELECT COUNT(*) as total_requests FROM api_request_logs;

-- 2. Recent requests (last 20)
SELECT 
    timestamp,
    method,
    path,
    status_code,
    response_time_ms,
    event_type,
    ip_address
FROM api_request_logs 
ORDER BY timestamp DESC 
LIMIT 20;

-- 3. Requests by endpoint
SELECT 
    path,
    COUNT(*) as request_count,
    AVG(response_time_ms) as avg_response_time,
    MIN(response_time_ms) as min_response_time,
    MAX(response_time_ms) as max_response_time
FROM api_request_logs 
WHERE response_time_ms IS NOT NULL
GROUP BY path 
ORDER BY request_count DESC;

-- 4. Requests by event type
SELECT 
    event_type,
    COUNT(*) as count,
    AVG(response_time_ms) as avg_response_time
FROM api_request_logs 
GROUP BY event_type 
ORDER BY count DESC;

-- 5. Error analysis
SELECT 
    status_code,
    COUNT(*) as error_count,
    path,
    event_type
FROM api_request_logs 
WHERE status_code >= 400
GROUP BY status_code, path, event_type
ORDER BY error_count DESC;

-- 6. Generate endpoint detailed stats
SELECT 
    timestamp,
    rag_query,
    rag_response_length,
    response_time_ms,
    status_code,
    chat_id
FROM api_request_logs 
WHERE event_type = 'rag_generate'
ORDER BY timestamp DESC 
LIMIT 10;

-- 7. User activity (for authenticated requests)
SELECT 
    user_id,
    COUNT(*) as request_count,
    MIN(timestamp) as first_request,
    MAX(timestamp) as last_request
FROM api_request_logs 
WHERE user_id IS NOT NULL
GROUP BY user_id
ORDER BY request_count DESC;

-- 8. Hourly request distribution (last 24 hours)
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    COUNT(*) as requests,
    AVG(response_time_ms) as avg_response_time
FROM api_request_logs 
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;

-- 9. RAG context usage analysis
SELECT 
    rag_context_used->>'chunks_count' as chunks_used,
    COUNT(*) as frequency,
    AVG(response_time_ms) as avg_response_time,
    AVG(rag_response_length) as avg_response_length
FROM api_request_logs 
WHERE rag_context_used IS NOT NULL
GROUP BY rag_context_used->>'chunks_count'
ORDER BY chunks_used::int;

-- 10. IP address analysis
SELECT 
    ip_address,
    COUNT(*) as request_count,
    COUNT(DISTINCT user_id) as unique_users,
    MIN(timestamp) as first_seen,
    MAX(timestamp) as last_seen
FROM api_request_logs 
WHERE ip_address IS NOT NULL
GROUP BY ip_address
ORDER BY request_count DESC
LIMIT 10;

-- 11. Performance analysis - slowest endpoints
SELECT 
    path,
    method,
    AVG(response_time_ms) as avg_time,
    MAX(response_time_ms) as max_time,
    COUNT(*) as request_count
FROM api_request_logs 
WHERE response_time_ms IS NOT NULL
GROUP BY path, method
HAVING COUNT(*) >= 5  -- Only endpoints with at least 5 requests
ORDER BY avg_time DESC
LIMIT 10;

-- 12. Recent generate queries with context
SELECT 
    timestamp,
    LEFT(rag_query, 100) as query_preview,
    rag_response_length,
    rag_context_used->>'chunks_count' as chunks_used,
    rag_context_used->>'total_context_length' as context_length,
    response_time_ms
FROM api_request_logs 
WHERE event_type = 'rag_generate' 
    AND rag_query IS NOT NULL
ORDER BY timestamp DESC 
LIMIT 15;
