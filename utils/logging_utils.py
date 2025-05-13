#!/usr/bin/env python3
"""
Logging utilities for Sumbird.

This module provides logging functionality:
- Error logging with consistent formatting
- API error handling
- Pipeline step logging
"""
import os
import sys
import traceback
from utils.date_utils import format_datetime

def log_error(module_name, error_message, exception=None):
    """Log an error with consistent formatting.
    
    Used across all modules for standardized error logging.
    
    Args:
        module_name (str): Name of the module where the error occurred
        error_message (str): Human-readable error message
        exception (Exception, optional): Exception object if available
    """
    timestamp = format_datetime()
    
    # Format the error message
    formatted_message = f"[ERROR] {timestamp} - {module_name}: {error_message}"
    
    # Print to console
    print(formatted_message, file=sys.stderr)
    
    # If there's an exception, print the traceback
    if exception:
        print(f"Exception details: {str(exception)}", file=sys.stderr)
        print("Traceback:", file=sys.stderr)
        traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Append to error log file
    with open(os.path.join('logs', 'error.log'), 'a', encoding='utf-8') as log_file:
        log_file.write(f"{formatted_message}\n")
        if exception:
            log_file.write(f"Exception details: {str(exception)}\n")
            log_file.write("Traceback:\n")
            traceback_text = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            log_file.write(f"{traceback_text}\n")
        log_file.write("---\n")
        
def handle_request_error(module_name, response, error_message):
    """Handle API request errors consistently.
    
    Used in: telegraph_publisher.py, telegram_distributer.py
    
    Args:
        module_name (str): Name of the module where the error occurred
        response: Response object from the request
        error_message (str): Base error message
        
    Returns:
        bool: Always returns False to indicate failure
    """
    full_message = f"{error_message} Status code: {response.status_code}"
    
    try:
        response_text = response.text
        full_message += f"\nResponse: {response_text}"
    except:
        pass
        
    log_error(module_name, full_message)
    return False

def log_step(log_file, status, message):
    """Log a pipeline step to the log file.
    
    Args:
        log_file: The open file handle to write to
        status: Boolean indicating success (True) or failure (False)
        message: The message to log
    """
    status_icon = "✅" if status else "❌"
    log_file.write(f"{status_icon} {message}\n") 