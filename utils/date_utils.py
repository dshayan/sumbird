#!/usr/bin/env python3
"""
Date and time utilities for Sumbird.

This module provides date and time handling functions:
- Date format conversions
- Timezone conversions
- Date range operations
"""
from datetime import datetime, timedelta

import pytz

DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_TZ_FORMAT = '%Y-%m-%d %H:%M:%S %Z'
TIME_FORMAT = '%H:%M'
LOG_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
FEED_DATETIME_FORMAT = '%Y-%m-%d %H:%M %Z'

# Timezone object from environment
# Will be set by env_utils during initialization
TIMEZONE = None

def set_timezone(timezone_str):
    """Set the global timezone object."""
    global TIMEZONE
    TIMEZONE = pytz.timezone(timezone_str)

def get_target_date(target_date_str=None):
    """Get the target date as a datetime object.
    
    Args:
        target_date_str (str, optional): Target date string in YYYY-MM-DD format.
            If None, uses yesterday.
            
    Returns:
        datetime: A timezone-aware datetime object for the start of the target day
        
    Raises:
        ValueError: If the date format is invalid
    """
    if not target_date_str:
        # Use yesterday instead of today
        return (datetime.now(TIMEZONE) - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        # Parse the date from the TARGET_DATE environment variable
        date_obj = datetime.strptime(target_date_str, DATE_FORMAT)
        # Add timezone information
        return TIMEZONE.localize(date_obj.replace(hour=0, minute=0, second=0, microsecond=0))
    except ValueError:
        raise ValueError(f"Invalid date format. Expected YYYY-MM-DD, got {target_date_str}")

def get_date_str(target_date=None):
    """Get the target date as a string in YYYY-MM-DD format.
    
    Args:
        target_date (datetime, optional): Target date. If None, calculates from environment.
        
    Returns:
        str: Date string in YYYY-MM-DD format
    """
    if target_date is None:
        target_date = get_target_date()
    return target_date.strftime(DATE_FORMAT)

def get_now():
    """Get current datetime with timezone information.
    
    Returns:
        datetime: Current time as timezone-aware datetime
    """
    return datetime.now(TIMEZONE)

def format_datetime(dt=None, include_timezone=True):
    """Format a datetime with consistent timezone handling.
    
    Args:
        dt (datetime, optional): Datetime object to format. If None, uses current time.
        include_timezone (bool): Whether to include timezone in the formatted string.
        
    Returns:
        str: Formatted datetime string
    """
    if dt is None:
        dt = get_now()
    elif dt.tzinfo is None:
        # Add timezone if it's naive
        dt = TIMEZONE.localize(dt)
    
    if include_timezone:
        return dt.strftime(DATETIME_TZ_FORMAT)
    else:
        return dt.strftime(DATETIME_FORMAT)

def format_log_datetime(dt=None):
    """Format datetime for log entries.
    
    Args:
        dt (datetime, optional): Datetime object to format. If None, uses current time.
        
    Returns:
        str: Formatted datetime string for logs
    """
    if dt is None:
        dt = get_now()
    elif dt.tzinfo is None:
        # Add timezone if it's naive
        dt = TIMEZONE.localize(dt)
    
    return dt.strftime(LOG_DATETIME_FORMAT)

def format_iso_datetime(dt=None):
    """Format datetime as ISO8601 string.
    
    Args:
        dt (datetime, optional): Datetime object to format. If None, uses current time.
        
    Returns:
        str: ISO8601 formatted datetime string
    """
    if dt is None:
        dt = get_now()
    elif dt.tzinfo is None:
        # Add timezone if it's naive
        dt = TIMEZONE.localize(dt)
    
    return dt.isoformat()

def format_feed_datetime(dt):
    """Format datetime for feed display.
    
    Args:
        dt (datetime): Timezone-aware datetime object to format.
        
    Returns:
        str: Formatted datetime string for feed display
    """
    if dt.tzinfo is None:
        # Add timezone if it's naive
        dt = TIMEZONE.localize(dt)
    
    return dt.strftime(FEED_DATETIME_FORMAT)

def get_date_range(target_date):
    """Get date range for the target date (full day).
    
    Args:
        target_date: A timezone-aware datetime object representing the start of the target day
        
    Returns:
        tuple: (start, end) datetime objects with timezone information preserved
    """
    # Start of the target day (already timezone-aware)
    target_start = target_date
    
    # Start of the next day (preserves timezone info)
    target_end = target_date + timedelta(days=1)
    
    return target_start, target_end

def convert_to_timezone(utc_time):
    """Convert UTC time to configured timezone.
    
    Takes a naive datetime object (from feedparser's time tuples) that represents 
    a UTC time, adds timezone information, and converts it to the configured 
    application timezone.
    
    Args:
        utc_time: A naive datetime object assumed to be in UTC
        
    Returns:
        datetime: A timezone-aware datetime object in the configured timezone
    """
    if not utc_time:
        return None
    
    # Directly create a timezone-aware UTC datetime
    utc_aware = pytz.UTC.localize(utc_time)
    
    # Convert to the target timezone
    local_dt = utc_aware.astimezone(TIMEZONE)
    return local_dt 