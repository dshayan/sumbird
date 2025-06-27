#!/usr/bin/env python3
"""
Retry utilities for Sumbird pipeline.
Provides simple retry mechanisms with configurable timeout and max attempts.
"""
import time
import asyncio
import signal
import threading
from typing import Callable, Any
from functools import wraps
from utils.logging_utils import log_error, log_retry


class TimeoutError(Exception):
    """Custom timeout exception."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Operation timed out")


def run_with_timeout(func, timeout_seconds, *args, **kwargs):
    """Run a function with timeout using threading (cross-platform)."""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        # Thread is still running, timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


def retry_sync(func: Callable, timeout: int = 60, max_attempts: int = 3, context: str = None) -> Callable:
    """
    Decorator for synchronous functions with retry logic and timeout.
    
    Args:
        func: Function to retry
        timeout: Timeout in seconds for each attempt
        max_attempts: Maximum number of attempts
        context: Human-readable description of what's being retried
        
    Returns:
        Wrapped function with retry logic and timeout
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        
        # Use a more readable module name
        module_name = 'Fetcher' if 'fetcher' in func.__module__ else func.__module__.split('.')[-1].title()
        
        # Generate context message if not provided
        operation_context = context or f"network operation ({func.__name__})"
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Apply timeout to each attempt
                if timeout > 0:
                    return run_with_timeout(func, timeout, *args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == max_attempts:
                    # Final attempt failed - use ERROR level
                    if isinstance(e, TimeoutError):
                        log_error(module_name, f"Operation timed out after {max_attempts} attempts: {operation_context}")
                    else:
                        log_error(module_name, f"Operation failed after {max_attempts} attempts: {operation_context}", e)
                    raise e
                
                # Log retry attempt with less alarming format
                if isinstance(e, TimeoutError):
                    retry_message = f"Operation timed out, retrying in 2s: {operation_context}"
                else:
                    retry_message = f"Operation failed, retrying in 2s: {operation_context}"
                
                log_retry(module_name, retry_message, attempt, max_attempts, e)
                time.sleep(2)  # Simple 2-second delay between retries
        
        # Should never reach here, but just in case
        raise last_exception
    
    return wrapper


def retry_async(func: Callable, timeout: int = 60, max_attempts: int = 3, context: str = None) -> Callable:
    """
    Decorator for asynchronous functions with retry logic.
    
    Args:
        func: Async function to retry
        timeout: Timeout in seconds (not used directly, kept for API consistency)
        max_attempts: Maximum number of attempts
        context: Human-readable description of what's being retried
        
    Returns:
        Wrapped async function with retry logic
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_exception = None
        
        # Use a more readable module name
        module_name = func.__module__.split('.')[-1].title()
        
        # Generate context message if not provided
        operation_context = context or f"async operation ({func.__name__})"
        
        for attempt in range(1, max_attempts + 1):
            try:
                if timeout > 0:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                else:
                    return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == max_attempts:
                    # Final attempt failed - use ERROR level
                    if isinstance(e, asyncio.TimeoutError):
                        log_error(module_name, f"Async operation timed out after {max_attempts} attempts: {operation_context}")
                    else:
                        log_error(module_name, f"Async operation failed after {max_attempts} attempts: {operation_context}", e)
                    raise e
                
                # Log retry attempt with less alarming format
                if isinstance(e, asyncio.TimeoutError):
                    retry_message = f"Async operation timed out, retrying in 2s: {operation_context}"
                else:
                    retry_message = f"Async operation failed, retrying in 2s: {operation_context}"
                
                log_retry(module_name, retry_message, attempt, max_attempts, e)
                await asyncio.sleep(2)  # Simple 2-second delay between retries
        
        # Should never reach here, but just in case
        raise last_exception
    
    return wrapper


def with_retry_sync(timeout: int = 60, max_attempts: int = 3, context: str = None):
    """
    Decorator factory for synchronous functions with configurable retry parameters.
    
    Args:
        timeout: Timeout in seconds for each attempt
        max_attempts: Maximum number of attempts
        context: Human-readable description of what's being retried
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        return retry_sync(func, timeout, max_attempts, context)
    return decorator


def with_retry_async(timeout: int = 60, max_attempts: int = 3, context: str = None):
    """
    Decorator factory for asynchronous functions with configurable retry parameters.
    
    Args:
        timeout: Timeout in seconds for each attempt
        max_attempts: Maximum number of attempts
        context: Human-readable description of what's being retried
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        return retry_async(func, timeout, max_attempts, context)
    return decorator 