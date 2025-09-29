#!/usr/bin/env python3
"""
Module for publishing content to Telegraph.
This module can be run independently or as part of the pipeline.
"""
import os
import json
import httpx
from datetime import datetime

from config import (
    CONVERTED_DIR, PUBLISHED_DIR, FILE_FORMAT,
    get_date_str, TELEGRAPH_ACCESS_TOKEN, get_file_path, TIMEZONE,
    format_iso_datetime, TELEGRAPH_TIMEOUT, RETRY_MAX_ATTEMPTS
)
from utils.logging_utils import log_error, handle_request_error, log_info, log_success, log_warning
from utils.retry_utils import with_retry_sync

@with_retry_sync(timeout=TELEGRAPH_TIMEOUT, max_attempts=RETRY_MAX_ATTEMPTS)
def create_or_update_telegraph_page(data, page_path=None):
    """Create or update a Telegraph page with retry logic.
    
    Args:
        data (dict): The page data including title, content, etc.
        page_path (str, optional): Existing page path to update. If None, a new page is created.
    
    Returns:
        dict or None: Response data from Telegraph API or None if failed
    """
    try:
        api_url = "https://api.telegra.ph/createPage"
        method = "POST"
        
        if page_path:
            api_url = "https://api.telegra.ph/editPage/" + page_path
        
        # Process content - we need to send it as a JSON string to the API
        content = data.get("content", [])
        
        # Convert content to JSON string if it's a list (not already a string)
        if isinstance(content, list):
            content_json = json.dumps(content)
        else:
            content_json = content
        
        # Prepare the request data
        request_data = {
            "access_token": TELEGRAPH_ACCESS_TOKEN,
            "title": data.get("title", "AI Updates on " + data.get("date", "")),
            "content": content_json,
            "author_name": data.get("author", "Sumbird Bot")
        }
        
        # Make the API request
        response = httpx.request(
            method, 
            api_url,
            data=request_data,
            timeout=TELEGRAPH_TIMEOUT
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get("ok"):
                return response_json.get("result")
            else:
                log_error('TelegraphPublisher', f"Telegraph API error: {response_json.get('error')}")
                return None
        else:
            log_error('TelegraphPublisher', f"API request failed with status code {response.status_code}\nResponse: {response.text}")
            return None
    
    except Exception as e:
        log_error('TelegraphPublisher', f"Error publishing to Telegraph", e)
        return None

def save_published_data(date_str, published_data):
    """Save published data to a file.
    
    Args:
        date_str (str): Date string for the file
        published_data (dict): Data about the published page
    
    Returns:
        str: Path to the saved file
    """
    output_file = get_file_path('published', date_str)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save the data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(published_data, f, ensure_ascii=False, indent=2)
    
    return output_file

def check_existing_publication(date_str, lang=None):
    """Check if there's an existing publication for the date and language.
    
    Args:
        date_str (str): Date string to check
        lang (str, optional): Language code (e.g., 'FA' for Persian)
    
    Returns:
        str or None: Page path if exists, None otherwise
    """
    published_file = get_file_path('published', date_str)
    
    if os.path.exists(published_file):
        try:
            with open(published_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if lang == 'FA':
                    return data.get("fa_path")
                else:
                    return data.get("path")
        except Exception as e:
            log_error('TelegraphPublisher', f"Error reading published file", e)
    
    return None

def publish(feeds_success=0):
    """Main function to publish converted content to Telegraph.
    
    Args:
        feeds_success (int): Number of successfully fetched feeds
    
    Returns:
        str or None: Path to the saved published file or None if failed
    """
    # Get the date string
    date_str = get_date_str()
    
    # Generate file paths using the centralized function
    en_input_file = get_file_path('converted', date_str)
    fa_input_file = get_file_path('converted', date_str, lang='FA')
    
    # Check if both required input files exist
    if not os.path.exists(en_input_file):
        log_error('TelegraphPublisher', f"English input file not found at {en_input_file}")
        return None
    
    if not os.path.exists(fa_input_file):
        log_error('TelegraphPublisher', f"Persian input file not found at {fa_input_file}")
        return None
    
    try:
        # Read the English converted file
        with open(en_input_file, 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        
        # Read the Persian converted file (now required)
        with open(fa_input_file, 'r', encoding='utf-8') as f:
            fa_data = json.load(f)
        
        # Check for existing publications
        en_existing_page_path = check_existing_publication(date_str)
        fa_existing_page_path = check_existing_publication(date_str, 'FA')
        
        # Publish English version
        if en_existing_page_path:
            log_info('TelegraphPublisher', f"Found existing English publication for {date_str}, updating...")
            en_result = create_or_update_telegraph_page(en_data, en_existing_page_path)
            en_action = "updated"
        else:
            log_info('TelegraphPublisher', f"Creating new English Telegraph page for {date_str}...")
            en_result = create_or_update_telegraph_page(en_data)
            en_action = "created"
        
        # Publish Persian version (now required)
        if fa_existing_page_path:
            log_info('TelegraphPublisher', f"Found existing Persian publication for {date_str}, updating...")
            fa_result = create_or_update_telegraph_page(fa_data, fa_existing_page_path)
            fa_action = "updated"
        else:
            log_info('TelegraphPublisher', f"Creating new Persian Telegraph page for {date_str}...")
            fa_result = create_or_update_telegraph_page(fa_data)
            fa_action = "created"
        
        # Check if both publications were successful
        if not en_result:
            log_error('TelegraphPublisher', "Failed to publish English content to Telegraph")
            return None
        
        if not fa_result:
            log_error('TelegraphPublisher', "Failed to publish Persian content to Telegraph")
            return None
        
        # Save published data
        published_data = {
            "title": en_data.get("title"),
            "url": en_result.get("url"),
            "path": en_result.get("path"),
            "fa_title": fa_data.get("title"),
            "fa_url": fa_result.get("url"),
            "fa_path": fa_result.get("path"),
            "published_date": format_iso_datetime(),
            "source_date": date_str,
            "feeds_success": feeds_success  # Include the feed success count
        }
        
        saved_file = save_published_data(date_str, published_data)
        log_success('TelegraphPublisher', f"Published data saved to {saved_file}")
        
        # Log success messages
        en_url = en_result.get('url')
        fa_url = fa_result.get('url')
        
        log_success('TelegraphPublisher', f"Successfully {en_action} English content on Telegraph: {en_url}")
        log_success('TelegraphPublisher', f"Successfully {fa_action} Persian content on Telegraph: {fa_url}")
        
        # Log completion
        log_success('TelegraphPublisher', f"Publisher completed. Output file: {saved_file}")
        
        return saved_file
    
    except Exception as e:
        log_error('TelegraphPublisher', f"Error publishing content", e)
        return None

if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(CONVERTED_DIR):
        log_info('TelegraphPublisher', f"Creating directory: {CONVERTED_DIR}")
        os.makedirs(CONVERTED_DIR, exist_ok=True)
    
    if not os.path.exists(PUBLISHED_DIR):
        log_info('TelegraphPublisher', f"Creating directory: {PUBLISHED_DIR}")
        os.makedirs(PUBLISHED_DIR, exist_ok=True)
    
    published_file = publish()
    if published_file:
        log_success('TelegraphPublisher', f"Publisher completed. Output file: {published_file}")
    else:
        log_error('TelegraphPublisher', "Publisher failed.") 