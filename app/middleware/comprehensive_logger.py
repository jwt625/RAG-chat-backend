"""
Comprehensive API request logging middleware
Logs all requests with special handling for generate endpoints
"""
import time
import json
import psutil
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from collections import deque
from fastapi import Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..database import SessionLocal
from ..models import ApiRequestLog

# Configure file logger as backup
file_logger = logging.getLogger('api_requests')
file_handler = logging.FileHandler('logs/api_requests.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
file_logger.addHandler(file_handler)
file_logger.setLevel(logging.INFO)

# In-memory buffer for recent requests (last 100)
REQUEST_BUFFER = deque(maxlen=100)

class ComprehensiveLogger:
    """Comprehensive API request logger with memory monitoring"""
    
    def __init__(self):
        self.enabled = True
        self.min_memory_mb = 50  # Minimum free memory to continue logging
        self.batch_size = 10  # Batch database writes
        self.pending_logs = []
        
    def is_memory_available(self) -> bool:
        """Check if enough memory is available for logging"""
        try:
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
            return available_mb > self.min_memory_mb
        except:
            return True  # If we can't check memory, assume it's available
    
    async def log_request(self, request: Request, response: Response, 
                         response_time_ms: float, additional_data: Dict[str, Any] = None):
        """Log comprehensive request information"""
        
        if not self.enabled or not self.is_memory_available():
            return
        
        try:
            # Extract user information from request state
            user_id = getattr(request.state, 'user_id', None)
            
            # Determine event type
            event_type = self._determine_event_type(request, response)
            
            # Get request size
            request_size = 0
            if hasattr(request, '_body'):
                request_size = len(request._body)
            elif 'content-length' in request.headers:
                try:
                    request_size = int(request.headers['content-length'])
                except:
                    request_size = 0
            
            # Get response size
            response_size = None
            if hasattr(response, 'body'):
                response_size = len(response.body)
            elif 'content-length' in response.headers:
                try:
                    response_size = int(response.headers['content-length'])
                except:
                    pass
            
            # Create log entry
            log_entry = {
                'timestamp': datetime.utcnow(),
                'method': request.method,
                'path': str(request.url.path)[:200],
                'query_params': str(request.url.query)[:1000] if request.url.query else None,
                'status_code': response.status_code,
                'response_time_ms': response_time_ms,
                'user_id': user_id,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.headers.get('user-agent', '')[:500],
                'event_type': event_type,
                'request_size_bytes': request_size,
                'response_size_bytes': response_size,
                'details': None
            }
            
            # Add additional data (for generate endpoints)
            if additional_data:
                log_entry.update(additional_data)
                
            # Add basic details for context
            details = {
                'referer': request.headers.get('referer', ''),
                'origin': request.headers.get('origin', ''),
                'accept': request.headers.get('accept', '')[:100]
            }
            log_entry['details'] = json.dumps(details)[:500]
            
            # Add to in-memory buffer
            REQUEST_BUFFER.append(log_entry.copy())
            
            # Async database write
            asyncio.create_task(self._write_to_database(log_entry))
            
        except Exception as e:
            # Log the error but don't break the request
            file_logger.error(f"Error in comprehensive logger: {str(e)}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address, handling proxies"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else 'unknown'
    
    def _determine_event_type(self, request: Request, response: Response) -> str:
        """Determine the type of event for categorization"""
        path = request.url.path.lower()
        
        if response.status_code >= 500:
            return 'server_error'
        elif response.status_code == 429:
            return 'rate_limit'
        elif response.status_code == 401:
            return 'auth_failure'
        elif response.status_code == 403:
            return 'auth_forbidden'
        elif path.startswith('/auth'):
            if response.status_code >= 400:
                return 'auth_error'
            return 'authentication'
        elif 'generate' in path:
            return 'rag_generate'
        elif path.startswith('/rag'):
            return 'rag_operation'
        elif path in ['/', '/docs', '/openapi.json']:
            return 'system'
        else:
            return 'general'
    
    async def _write_to_database(self, log_entry: Dict[str, Any]):
        """Write log entry to database with error handling"""
        try:
            db = SessionLocal()
            try:
                # Create database object
                db_log = ApiRequestLog(**log_entry)
                db.add(db_log)
                db.commit()
            finally:
                db.close()
                
        except SQLAlchemyError as e:
            # Database error - fallback to file logging
            await self._write_to_file(log_entry, db_error=str(e))
        except Exception as e:
            # Any other error - fallback to file logging
            await self._write_to_file(log_entry, error=str(e))
    
    async def _write_to_file(self, log_entry: Dict[str, Any], db_error: str = None, error: str = None):
        """Fallback file logging"""
        try:
            if db_error:
                log_entry['db_error'] = db_error
            if error:
                log_entry['general_error'] = error
                
            # Convert datetime to string for JSON serialization
            log_entry_copy = log_entry.copy()
            if 'timestamp' in log_entry_copy:
                log_entry_copy['timestamp'] = log_entry_copy['timestamp'].isoformat()
                
            file_logger.info(json.dumps(log_entry_copy, default=str))
        except Exception as e:
            # Last resort - basic logging
            file_logger.error(f"Failed to log request: {str(e)}")
    
    def get_recent_requests(self, limit: int = 50) -> list:
        """Get recent requests from in-memory buffer"""
        return list(REQUEST_BUFFER)[-limit:]
    
    def disable_logging(self):
        """Emergency disable logging"""
        self.enabled = False
        
    def enable_logging(self):
        """Re-enable logging"""
        self.enabled = True

# Global logger instance
comprehensive_logger = ComprehensiveLogger()


async def log_rag_request(request: Request, response: Response, 
                         response_time_ms: float, query_data: Dict[str, Any], 
                         context_used: list, response_text: str, 
                         chat_id: Optional[int] = None):
    """Enhanced logging specifically for RAG generate endpoints"""
    
    # Prepare RAG-specific data
    rag_context_summary = {
        'chunks_count': len(context_used),
        'total_context_length': sum(len(str(chunk.get('content', ''))) for chunk in context_used),
        'sources': [chunk.get('metadata', {}).get('title', 'Unknown') for chunk in context_used[:5]],
        'distances': [chunk.get('distance', 0) for chunk in context_used[:5]]
    }
    
    additional_data = {
        'rag_query': str(query_data.get('query', ''))[:2000],  # Truncate long queries
        'rag_context_used': rag_context_summary,
        'rag_response_length': len(response_text),
        'chat_id': chat_id,
        'details': json.dumps({
            'context_limit': query_data.get('context_limit', 3),
            'model_used': 'deepseek',
            'success': response.status_code == 200,
            'has_chat_history': bool(query_data.get('message_history')),
            'chat_history_length': len(query_data.get('message_history', []))
        })[:500]
    }
    
    await comprehensive_logger.log_request(request, response, response_time_ms, additional_data)
