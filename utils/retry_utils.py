#!/usr/bin/env python3
"""
Simplified retry utilities for Sumbird.
Provides retry mechanisms without complex timeout handling.
"""
import asyncio
import time
from functools import wraps
from typing import Callable, Optional

from utils.logging_utils import log_error, log_retry


def with_retry_sync(max_attempts: int = 3, module_name: Optional[str] = None, context: Optional[str] = None):
    """
    Decorator for synchronous functions with retry logic.
    
    Note: This decorator does NOT enforce timeouts. Timeout handling should be done
    at the HTTP client level (e.g., httpx timeout parameter, requests timeout, etc.).
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        module_name: Module name for logging (e.g., "Fetcher"). Auto-detected if not provided.
        context: Human-readable description of what's being retried (optional)
        
    Returns:
        Decorator function
        
    Example:
        @with_retry_sync(max_attempts=3, module_name="Fetcher")
        def fetch_data():
            return requests.get(url, timeout=30)  # Timeout handled by requests
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Determine module name for logging
            if module_name:
                name = module_name
            else:
                # Auto-detect from function module
                name = func.__module__.split('.')[-1].title().replace('_', '')
            
            # Generate context message if not provided
            operation_context = context or func.__name__
            
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        # Final attempt failed
                        log_error(name, f"Operation '{operation_context}' failed after {max_attempts} attempts", e)
                        raise
                    
                    # Log retry attempt
                    log_retry(name, f"Operation '{operation_context}' failed, retrying in 2s", attempt, max_attempts, e)
                    time.sleep(2)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def with_retry_async(timeout: int = 60, max_attempts: int = 3, module_name: Optional[str] = None, context: Optional[str] = None):
    """
    Decorator for asynchronous functions with retry logic and timeout.
    
    Args:
        timeout: Timeout per attempt in seconds (enforced via asyncio.wait_for)
        max_attempts: Maximum number of attempts (default: 3)
        module_name: Module name for logging. Auto-detected if not provided.
        context: Human-readable description of what's being retried (optional)
        
    Returns:
        Decorator function
        
    Example:
        @with_retry_async(timeout=120, max_attempts=3, module_name="OpenRouter")
        async def generate_text():
            return await client.generate(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine module name for logging
            if module_name:
                name = module_name
            else:
                # Auto-detect from function module
                name = func.__module__.split('.')[-1].title().replace('_', '')
            
            # Generate context message if not provided
            operation_context = context or func.__name__
            
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    if timeout > 0:
                        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    else:
                        return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        # Final attempt failed
                        if isinstance(e, asyncio.TimeoutError):
                            log_error(name, f"Async operation '{operation_context}' timed out after {max_attempts} attempts (timeout: {timeout}s)", e)
                        else:
                            log_error(name, f"Async operation '{operation_context}' failed after {max_attempts} attempts", e)
                        raise
                    
                    # Log retry attempt
                    if isinstance(e, asyncio.TimeoutError):
                        log_retry(name, f"Async operation '{operation_context}' timed out, retrying in 2s", attempt, max_attempts, e)
                    else:
                        log_retry(name, f"Async operation '{operation_context}' failed, retrying in 2s", attempt, max_attempts, e)
                    
                    await asyncio.sleep(2)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator
