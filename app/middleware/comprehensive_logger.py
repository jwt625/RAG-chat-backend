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
        """Log comprehensive request information - NEVER interrupts normal workflow"""

        try:
            # Early exit if logging disabled or low memory
            if not self.enabled or not self.is_memory_available():
                return
            # Safely extract user information
            user_id = None
            try:
                user_id = getattr(request.state, 'user_id', None)
            except:
                pass

            # Safely determine event type
            event_type = 'general'
            try:
                event_type = self._determine_event_type(request, response)
            except:
                pass

            # Safely get request size
            request_size = 0
            try:
                if hasattr(request, '_body') and request._body:
                    request_size = len(request._body)
                elif 'content-length' in request.headers:
                    request_size = int(request.headers['content-length'])
            except:
                request_size = 0

            # Safely get response size
            response_size = None
            try:
                if hasattr(response, 'body') and response.body is not None:
                    response_size = len(response.body)
                elif 'content-length' in response.headers:
                    response_size = int(response.headers['content-length'])
            except:
                pass
            
            # Safely create log entry
            log_entry = {}
            try:
                log_entry = {
                    'timestamp': datetime.utcnow(),
                    'method': str(request.method)[:10] if hasattr(request, 'method') else 'UNKNOWN',
                    'path': str(request.url.path)[:200] if hasattr(request, 'url') else '/unknown',
                    'status_code': int(response.status_code) if hasattr(response, 'status_code') else 500,
                    'response_time_ms': float(response_time_ms) if response_time_ms else 0.0,
                    'user_id': user_id,
                    'ip_address': self._get_client_ip(request),
                    'user_agent': str(request.headers.get('user-agent', ''))[:500] if hasattr(request, 'headers') else '',
                    'event_type': str(event_type)[:20],
                    'request_size_bytes': int(request_size),
                    'response_size_bytes': int(response_size) if response_size else None,
                    'details': None
                }

                # Safely add additional data (for generate endpoints)
                if additional_data and isinstance(additional_data, dict):
                    try:
                        log_entry.update(additional_data)
                    except:
                        pass

                # Safely add basic details for context
                try:
                    details = {
                        'referer': str(request.headers.get('referer', ''))[:100] if hasattr(request, 'headers') else '',
                        'origin': str(request.headers.get('origin', ''))[:100] if hasattr(request, 'headers') else '',
                        'accept': str(request.headers.get('accept', ''))[:100] if hasattr(request, 'headers') else '',
                        'query_params': str(request.url.query)[:200] if hasattr(request, 'url') and request.url.query else None
                    }
                    log_entry['details'] = json.dumps(details)[:500]
                except:
                    log_entry['details'] = '{"error": "failed_to_parse_details"}'

                # Safely add to in-memory buffer
                try:
                    REQUEST_BUFFER.append(log_entry.copy())
                except:
                    pass

                # Safely start async database write (fire and forget)
                try:
                    asyncio.create_task(self._write_to_database(log_entry))
                except:
                    # If async task creation fails, try direct file logging
                    try:
                        asyncio.create_task(self._write_to_file(log_entry, error="async_task_failed"))
                    except:
                        pass  # Ultimate fallback - just continue

            except Exception as e:
                # If everything fails, try minimal file logging
                try:
                    minimal_log = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'error': f'logging_failed: {str(e)}',
                        'path': str(getattr(request, 'url', {}).path) if hasattr(request, 'url') else 'unknown'
                    }
                    file_logger.error(json.dumps(minimal_log))
                except:
                    pass  # Ultimate fallback - just continue
            
        except Exception as e:
            # NEVER let logging errors break the request - just log to file and continue
            try:
                file_logger.error(f"Critical error in comprehensive logger: {str(e)}")
            except:
                pass  # Even file logging failed - just continue silently
    
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
        """Write log entry to database with comprehensive error handling - NEVER fails"""
        db = None
        try:
            # Validate log_entry has required fields
            if not isinstance(log_entry, dict):
                raise ValueError("log_entry must be a dictionary")

            # Ensure required fields exist with safe defaults
            safe_log_entry = {
                'timestamp': log_entry.get('timestamp', datetime.utcnow()),
                'method': str(log_entry.get('method', 'UNKNOWN'))[:10],
                'path': str(log_entry.get('path', '/unknown'))[:200],
                'status_code': int(log_entry.get('status_code', 500)),
                'response_time_ms': float(log_entry.get('response_time_ms', 0.0)) if log_entry.get('response_time_ms') else None,
                'user_id': log_entry.get('user_id'),
                'ip_address': str(log_entry.get('ip_address', ''))[:45] if log_entry.get('ip_address') else None,
                'user_agent': str(log_entry.get('user_agent', ''))[:500] if log_entry.get('user_agent') else None,
                'event_type': str(log_entry.get('event_type', 'general'))[:20],
                'request_size_bytes': int(log_entry.get('request_size_bytes', 0)) if log_entry.get('request_size_bytes') else None,
                'response_size_bytes': int(log_entry.get('response_size_bytes', 0)) if log_entry.get('response_size_bytes') else None,
                'details': str(log_entry.get('details', ''))[:500] if log_entry.get('details') else None,
                'rag_query': str(log_entry.get('rag_query', ''))[:2000] if log_entry.get('rag_query') else None,
                'rag_context_used': log_entry.get('rag_context_used'),
                'rag_response_length': int(log_entry.get('rag_response_length', 0)) if log_entry.get('rag_response_length') else None,
                'chat_id': int(log_entry.get('chat_id')) if log_entry.get('chat_id') else None
            }

            db = SessionLocal()
            db_log = ApiRequestLog(**safe_log_entry)
            db.add(db_log)
            db.commit()

        except SQLAlchemyError as e:
            # Database error - fallback to file logging
            try:
                await self._write_to_file(log_entry, db_error=str(e))
            except:
                pass
        except Exception as e:
            # Any other error - fallback to file logging
            try:
                await self._write_to_file(log_entry, error=str(e))
            except:
                pass
        finally:
            # Always close database connection safely
            try:
                if db:
                    db.close()
            except:
                pass
    
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
    """Enhanced logging specifically for RAG generate endpoints - NEVER fails"""

    try:
        # Safely prepare RAG-specific data
        rag_context_summary = {}
        try:
            context_used = context_used or []
            rag_context_summary = {
                'chunks_count': len(context_used),
                'total_context_length': sum(len(str(chunk.get('content', ''))) for chunk in context_used if isinstance(chunk, dict)),
                'sources': [chunk.get('metadata', {}).get('title', 'Unknown') for chunk in context_used[:5] if isinstance(chunk, dict)],
                'distances': [chunk.get('distance', 0) for chunk in context_used[:5] if isinstance(chunk, dict)]
            }
        except:
            rag_context_summary = {'error': 'failed_to_parse_context'}

        # Safely prepare additional data
        additional_data = {}
        try:
            query_data = query_data or {}
            response_text = response_text or ''

            additional_data = {
                'rag_query': str(query_data.get('query', ''))[:2000] if query_data.get('query') else None,
                'rag_context_used': rag_context_summary,
                'rag_response_length': len(str(response_text)) if response_text else 0,
                'chat_id': int(chat_id) if chat_id else None
            }

            # Safely create details JSON
            try:
                details_dict = {
                    'context_limit': query_data.get('context_limit', 3),
                    'model_used': 'deepseek',
                    'success': getattr(response, 'status_code', 500) == 200,
                    'has_chat_history': bool(query_data.get('message_history')),
                    'chat_history_length': len(query_data.get('message_history', []))
                }
                additional_data['details'] = json.dumps(details_dict)[:500]
            except:
                additional_data['details'] = '{"error": "failed_to_create_details"}'

        except Exception as e:
            additional_data = {
                'rag_query': 'error_parsing_query',
                'rag_response_length': 0,
                'details': f'{{"error": "rag_logging_failed: {str(e)[:100]}"}}'
            }

        # Safely call the main logger (fire and forget)
        try:
            await comprehensive_logger.log_request(request, response, response_time_ms, additional_data)
        except:
            pass  # Never let logging break the RAG response

    except Exception as e:
        # Ultimate fallback - try minimal file logging
        try:
            file_logger.error(f"RAG logging completely failed: {str(e)}")
        except:
            pass  # Even file logging failed - just continue
