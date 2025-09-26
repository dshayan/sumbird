#!/usr/bin/env python3
"""
Logging utilities for Sumbird.

This module provides logging functionality:
- Error logging with consistent formatting
- API error handling
- Pipeline step logging
- Info and success logging
- Retry logging for network operations
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

def log_retry(module_name, message, attempt, max_attempts, exception=None):
    """Log a retry attempt with less alarming formatting.
    
    Used for network operations that are expected to occasionally fail and retry.
    
    Args:
        module_name (str): Name of the module logging the retry
        message (str): Human-readable description of what's being retried
        attempt (int): Current attempt number
        max_attempts (int): Maximum number of attempts
        exception (Exception, optional): Exception that caused the retry
    """
    timestamp = format_datetime()
    formatted_message = f"[RETRY] {timestamp} - {module_name}: {message} (attempt {attempt}/{max_attempts})"
    
    # Print to console with less alarming stderr
    print(formatted_message)
    
    # For timeouts and network errors, don't log full traceback to avoid alarm
    # Only log the exception message if it's informative
    if exception and not (exception.__class__.__name__ == 'TimeoutError' or isinstance(exception, ConnectionError)):
        print(f"Reason: {str(exception)}")

def log_info(module_name, message):
    """Log an informational message with consistent formatting.
    
    Used for general information, progress updates, and status messages.
    
    Args:
        module_name (str): Name of the module logging the message
        message (str): The informational message
    """
    timestamp = format_datetime()
    formatted_message = f"[INFO] {timestamp} - {module_name}: {message}"
    print(formatted_message)

def log_success(module_name, message):
    """Log a success message with consistent formatting.
    
    Used for successful operations and completions.
    
    Args:
        module_name (str): Name of the module logging the message
        message (str): The success message
    """
    timestamp = format_datetime()
    formatted_message = f"[SUCCESS] {timestamp} - {module_name}: {message}"
    print(formatted_message)

def log_warning(module_name, message):
    """Log a warning message with consistent formatting.
    
    Used for non-critical issues that should be noted.
    
    Args:
        module_name (str): Name of the module logging the message
        message (str): The warning message
    """
    timestamp = format_datetime()
    formatted_message = f"[WARNING] {timestamp} - {module_name}: {message}"
    print(formatted_message, file=sys.stderr)

def log_pipeline_step(step_name, message=""):
    """Log a pipeline step with consistent formatting.
    
    Used in main.py and test_main.py for pipeline step headers.
    
    Args:
        step_name (str): Name of the pipeline step
        message (str, optional): Additional message for the step
    """
    if message:
        print(f"\n=== {step_name}: {message} ===")
    else:
        print(f"\n=== {step_name} ===")

def log_pipeline_progress(step_number, total_steps, step_name, message=""):
    """Log a pipeline step with modern progress formatting.
    
    Args:
        step_number (int): Current step number (1-based)
        total_steps (int): Total number of steps
        step_name (str): Name of the pipeline step
        message (str, optional): Additional message for the step
    """
    timestamp = format_datetime()
    if message:
        formatted_message = f"[INFO] {timestamp} - Pipeline: Step {step_number}/{total_steps}: {step_name} - {message}"
    else:
        formatted_message = f"[INFO] {timestamp} - Pipeline: Step {step_number}/{total_steps}: {step_name}..."
    print(formatted_message)
        
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