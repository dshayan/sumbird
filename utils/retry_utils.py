#!/usr/bin/env python3
"""
Retry utilities for Sumbird pipeline.
Provides simple retry mechanisms with configurable timeout and max attempts.
"""
import time
import asyncio
from typing import Callable, Any
from functools import wraps
from utils.logging_utils import log_error


def retry_sync(func: Callable, timeout: int = 60, max_attempts: int = 3) -> Callable:
    """
    Decorator for synchronous functions with retry logic.
    
    Args:
        func: Function to retry
        timeout: Timeout in seconds (not used for sync, kept for API consistency)
        max_attempts: Maximum number of attempts
        
    Returns:
        Wrapped function with retry logic
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        module_name = getattr(func, '__module__', 'Unknown')
        
        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == max_attempts:
                    # Final attempt failed
                    log_error(module_name, f"Function {func.__name__} failed after {max_attempts} attempts", e)
                    raise e
                
                # Log retry attempt
                log_error(module_name, f"Function {func.__name__} attempt {attempt}/{max_attempts} failed, retrying in 2s", e)
                time.sleep(2)  # Simple 2-second delay between retries
        
        # Should never reach here, but just in case
        raise last_exception
    
    return wrapper


def retry_async(func: Callable, timeout: int = 60, max_attempts: int = 3) -> Callable:
    """
    Decorator for asynchronous functions with retry logic.
    
    Args:
        func: Async function to retry
        timeout: Timeout in seconds (not used directly, kept for API consistency)
        max_attempts: Maximum number of attempts
        
    Returns:
        Wrapped async function with retry logic
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        last_exception = None
        module_name = getattr(func, '__module__', 'Unknown')
        
        for attempt in range(1, max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == max_attempts:
                    # Final attempt failed
                    log_error(module_name, f"Async function {func.__name__} failed after {max_attempts} attempts", e)
                    raise e
                
                # Log retry attempt
                log_error(module_name, f"Async function {func.__name__} attempt {attempt}/{max_attempts} failed, retrying in 2s", e)
                await asyncio.sleep(2)  # Simple 2-second delay between retries
        
        # Should never reach here, but just in case
        raise last_exception
    
    return wrapper


def with_retry_sync(timeout: int = 60, max_attempts: int = 3):
    """
    Decorator factory for synchronous functions with configurable retry parameters.
    
    Args:
        timeout: Timeout in seconds (kept for API consistency)
        max_attempts: Maximum number of attempts
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        return retry_sync(func, timeout, max_attempts)
    return decorator


def with_retry_async(timeout: int = 60, max_attempts: int = 3):
    """
    Decorator factory for asynchronous functions with configurable retry parameters.
    
    Args:
        timeout: Timeout in seconds (kept for API consistency)
        max_attempts: Maximum number of attempts
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        return retry_async(func, timeout, max_attempts)
    return decorator 