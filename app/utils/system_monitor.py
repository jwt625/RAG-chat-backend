import psutil
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_system_resources() -> Dict:
    """Get current system resource usage"""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "memory": {
            "total_mb": memory.total / (1024 * 1024),
            "available_mb": memory.available / (1024 * 1024),
            "used_mb": memory.used / (1024 * 1024),
            "percent": memory.percent
        },
        "disk": {
            "total_gb": disk.total / (1024 * 1024 * 1024),
            "free_gb": disk.free / (1024 * 1024 * 1024),
            "percent": disk.percent
        }
    }

def check_resources(memory_threshold: int = 80, disk_threshold: int = 80) -> bool:
    """Check if system has enough resources"""
    resources = get_system_resources()
    
    if resources["memory"]["percent"] > memory_threshold:
        logger.warning(f"Memory usage high: {resources['memory']['percent']}%")
        return False
        
    if resources["disk"]["percent"] > disk_threshold:
        logger.warning(f"Disk usage high: {resources['disk']['percent']}%")
        return False
    
    return True

def log_resource_usage(operation: str = ""):
    """Decorator to log resource usage"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            before = get_system_resources()
            logger.info(f"Starting {operation}. Memory usage: {before['memory']['percent']}%")
            
            result = await func(*args, **kwargs)
            
            after = get_system_resources()
            logger.info(
                f"Completed {operation}. "
                f"Memory usage: {after['memory']['percent']}% "
                f"(changed: {after['memory']['percent'] - before['memory']['percent']}%)"
            )
            return result
        return wrapper
    return decorator 