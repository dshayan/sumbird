#!/usr/bin/env python3
"""
Original RSS fetcher for Twitter/X feeds - Alternative implementation.

This module provides a simpler RSS fetching implementation without rate limiting
and advanced features. It can be used as a fallback or for testing purposes.
This module can be run independently or as part of the pipeline.
"""
import os
import sys
from datetime import datetime

import feedparser

from config import (
    BASE_URL, EXPORT_DIR, EXPORT_TITLE_FORMAT, HANDLES, RETRY_MAX_ATTEMPTS,
    RSS_TIMEOUT, TIMEZONE
)
from utils.date_utils import (
    convert_to_timezone, format_feed_datetime, get_date_range,
    get_date_str, get_target_date
)
from utils.file_utils import get_file_path
from utils.html_utils import clean_text, strip_html
from utils.logging_utils import log_error, log_info, log_success, log_warning
from utils.retry_utils import with_retry_sync

def convert_to_x_url(url):
    """Convert RSS feed URL to x.com format.
    
    Args:
        url (str): Original RSS feed URL
        
    Returns:
        str: Converted x.com URL
    """
    if not url:
        return url
    
    # Extract the domain from BASE_URL for URL parsing
    base_domain = BASE_URL.rstrip('/').split('://')[-1]  # Get domain part
    
    if base_domain in url and '/status/' in url:
        # Extract username and status ID from the URL
        url_parts = url.split(base_domain + '/')
        if len(url_parts) > 1:
            path = url_parts[1]
            if '/status/' in path:
                username = path.split('/status/')[0]
                status_id = path.split('/status/')[1].split('#')[0]
                return f"https://x.com/{username}/status/{status_id}"
    
    return url

def get_feeds_from_handles():
    """Generate feed URLs from Twitter handles."""
    feeds = []
    for handle in HANDLES:
        handle = handle.strip()
        if handle:
            feed_url = f"{BASE_URL}{handle}/rss"
            feed_title = f"@{handle}"
            feeds.append({
                'url': feed_url,
                'title': feed_title
            })
    return feeds

@with_retry_sync(timeout=RSS_TIMEOUT, max_attempts=RETRY_MAX_ATTEMPTS, context="RSS feed fetch")
def fetch_feed_with_retry(feed_url):
    """Fetch a single RSS feed with retry logic.
    
    Args:
        feed_url (str): URL of the RSS feed to fetch
        
    Returns:
        feedparser.FeedParserDict: Parsed feed data
    """
    return feedparser.parse(feed_url)

def fetch_feed_with_context(feed_title, feed_url):
    """Fetch a feed with contextual retry logging.
    
    Args:
        feed_title (str): Human-readable feed title (e.g., "@MistralAI")
        feed_url (str): URL of the RSS feed to fetch
        
    Returns:
        feedparser.FeedParserDict: Parsed feed data
    """
    # Create a context-aware retry decorator
    @with_retry_sync(timeout=RSS_TIMEOUT, max_attempts=RETRY_MAX_ATTEMPTS, 
                     context=f"RSS feed fetch for {feed_title}")
    def fetch_with_context():
        return feedparser.parse(feed_url)
    
    return fetch_with_context()

def get_posts(feeds, target_start, target_end):
    """Fetch posts from feeds within the specified date range."""
    results = []
    successful_feeds = 0
    failed_handles = []
    
    for feed in feeds:
        feed_handle = feed['title']  # e.g., "@username"
        
        try:
            # Use the context-aware fetch function
            parsed_feed = fetch_feed_with_context(feed['title'], feed['url'])
            
            # Analyze the parsed feed for detailed logging
            if parsed_feed.feed and hasattr(parsed_feed.feed, 'title'):
                # Feed was successfully parsed
                feed['title'] = parsed_feed.feed.title
                entry_count = len(parsed_feed.entries) if hasattr(parsed_feed, 'entries') else 0
                successful_feeds += 1
                log_success('Fetcher', f"{feed_handle} - Feed loaded successfully ({entry_count} entries found)")
            else:
                # Feed failed - analyze why
                failure_reason = analyze_feed_failure(parsed_feed, feed_handle)
                log_warning('Fetcher', f"{feed_handle} - Feed failed: {failure_reason}")
                handle = feed['title'].replace('@', '')
                failed_handles.append({'handle': handle, 'reason': failure_reason})
                continue
            
            for entry in parsed_feed.entries:
                pub_date = None
                
                # Convert time tuple to datetime and apply timezone
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    # Convert feedparser's time tuple to a datetime object and set timezone
                    naive_dt = datetime(*entry.published_parsed[:6])
                    pub_date = convert_to_timezone(naive_dt)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    # Use updated time if published time is not available
                    naive_dt = datetime(*entry.updated_parsed[:6])
                    pub_date = convert_to_timezone(naive_dt)
                else:
                    continue
                
                # Compare timezone-aware datetime objects directly
                if target_start <= pub_date < target_end:
                    # Check if this is a retweet by examining the title
                    title = entry.get('title', '')
                    is_retweet = title.startswith('RT by @')
                    
                    # Get the URL from the link field
                    url = entry.get('link', '')
                    
                    # Get content from summary/content fields
                    content = None
                    if hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].value
                    else:
                        content = entry.title
                    
                    # Clean the content
                    content = strip_html(content)
                    content = clean_text(content)
                    
                    # Convert URLs in content to x.com format
                    if content:
                        # Extract the domain from BASE_URL for URL replacement
                        base_domain = BASE_URL.rstrip('/').split('://')[-1]  # Get domain part
                        
                        # Replace URLs in content with x.com format
                        import re
                        # Pattern to match URLs with the base domain (with or without https://)
                        url_pattern = rf'(?:https?://)?{re.escape(base_domain)}/([^/\s]+)/status/(\d+)(?:#\w+)?'
                        content = re.sub(url_pattern, r'https://x.com/\1/status/\2', content)
                    
                    # Handle retweets
                    if is_retweet:
                        # Extract original author from the URL
                        original_author = "unknown"
                        if url and BASE_URL.rstrip('/') in url:
                            # Extract the domain from BASE_URL for URL parsing
                            base_domain = BASE_URL.rstrip('/').split('://')[-1]  # Get domain part
                            url_parts = url.split(base_domain + '/')
                            if len(url_parts) > 1:
                                path = url_parts[1]
                                if '/status/' in path:
                                    original_author = path.split('/status/')[0]
                        
                        # Format as "RT from @username: content"
                        content = f"RT from @{original_author}: {content}"
                    
                    # Convert the main URL to x.com format
                    converted_url = convert_to_x_url(url)
                    
                    results.append({
                        'source': feed['title'],
                        'content': content,
                        'url': converted_url,
                        'date': format_feed_datetime(pub_date),
                        'timestamp': pub_date
                    })
        except Exception as e:
            # This catches exceptions that weren't handled by the retry mechanism
            failure_reason = f"Exception: {str(e)}"
            log_error('Fetcher', f"{feed_handle} - Feed failed: {failure_reason}")
            handle = feed['title'].replace('@', '')
            failed_handles.append({'handle': handle, 'reason': failure_reason})
    
    results.sort(key=lambda x: x['timestamp'])
    return results, successful_feeds, failed_handles

def analyze_feed_failure(parsed_feed, feed_handle):
    """Analyze why a feed failed and return a descriptive reason.
    
    Args:
        parsed_feed: The parsed feed object from feedparser
        feed_handle: The feed handle (e.g., "@username")
    
    Returns:
        str: Human-readable failure reason
    """
    # Check for feedparser bozo (malformed feed) errors
    if hasattr(parsed_feed, 'bozo') and parsed_feed.bozo:
        if hasattr(parsed_feed, 'bozo_exception'):
            exception_type = type(parsed_feed.bozo_exception).__name__
            if 'URLError' in exception_type or 'HTTPError' in exception_type:
                return f"Network error ({exception_type})"
            elif 'XML' in exception_type or 'SAX' in exception_type:
                return f"Malformed RSS (XML parsing error)"
            else:
                return f"Feed parsing error ({exception_type})"
        else:
            return "Malformed RSS (bozo flag set)"
    
    # Check for HTTP status codes if available
    if hasattr(parsed_feed, 'status'):
        status = parsed_feed.status
        if status == 404:
            return "HTTP 404 (account not found)"
        elif status == 403:
            return "HTTP 403 (access denied/private account)"
        elif status == 429:
            return "HTTP 429 (rate limited)"
        elif status >= 500:
            return f"HTTP {status} (server error)"
        elif status >= 400:
            return f"HTTP {status} (client error)"
    
    # Check if feed object exists but is empty
    if hasattr(parsed_feed, 'feed'):
        if not parsed_feed.feed:
            return "Empty feed (no feed object)"
        elif not hasattr(parsed_feed.feed, 'title'):
            return "Invalid feed structure (no title)"
    
    # Check if entries exist
    if hasattr(parsed_feed, 'entries'):
        if len(parsed_feed.entries) == 0:
            return "Empty feed (no entries)"
    
    # Default fallback
    return "Unknown error (feed validation failed)"

def save_to_file(posts, output_file, date_str):
    """Save processed posts to output file."""
    if not posts:
        log_info('Fetcher', "No posts found to save")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# No Twitter Posts Found")
        return
    
    posts_by_date = {}
    for post in posts:
        date_only = post['date'].split(' ')[0]
        time_only = post['date'].split(' ')[1]
        
        if date_only not in posts_by_date:
            posts_by_date[date_only] = {}
        
        source = post['source']
        if source not in posts_by_date[date_only]:
            posts_by_date[date_only][source] = []
        
        posts_by_date[date_only][source].append({
            'time': time_only,
            'content': post['content'],
            'url': post['url'],
            'timestamp': post['timestamp']
        })
    
    sorted_dates = sorted(posts_by_date.keys())
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(EXPORT_TITLE_FORMAT.format(date=date_str) + " (Timezone: " + str(TIMEZONE) + ")\n\n")
        
        for date in sorted_dates:
            sorted_sources = sorted(posts_by_date[date].keys())
            
            for source in sorted_sources:
                f.write(f"{source}:\n\n")
                
                source_posts = posts_by_date[date][source]
                source_posts.sort(key=lambda x: x['timestamp'])
                
                for post in source_posts:
                    f.write(f"- {post['time']}: {post['content']} [URL: {post['url']}]\n")
                
                f.write("\n")

def fetch_and_format():
    """Main function to fetch and format tweets."""
    # Get the target date
    target_date = get_target_date()
    date_str = get_date_str()
    
    # Generate output file path using the centralized function
    output_file = get_file_path('export', date_str)
    
    log_info('Fetcher', f"Base URL: {BASE_URL}")
    log_info('Fetcher', f"Handles to process: {', '.join(HANDLES)}")
    log_info('Fetcher', f"Target date: {date_str}")
    
    # Get feeds and posts
    feeds = get_feeds_from_handles()
    feeds_total = len(feeds)
    
    target_start, target_end = get_date_range(target_date)
    posts, feeds_success, failed_handles = get_posts(feeds, target_start, target_end)
    
    log_info('Fetcher', f"Retrieved {len(posts)} posts from {feeds_success}/{feeds_total} feeds")
    
    # Log failed feeds summary if there are any failures
    if failed_handles:
        log_info('Fetcher', f"Failed feeds summary:")
        for failed_feed in failed_handles:
            log_info('Fetcher', f"- {failed_feed['handle']}: {failed_feed['reason']}")
    
    # Save to file
    save_to_file(posts, output_file, date_str)
    
    return output_file, feeds_success, feeds_total, failed_handles

if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(EXPORT_DIR):
        log_info('Fetcher', f"Creating directory: {EXPORT_DIR}")
        os.makedirs(EXPORT_DIR, exist_ok=True)
    
    output_file, feeds_success, feeds_total, failed_handles = fetch_and_format()
    if output_file and os.path.exists(output_file):
        log_success('Fetcher', f"Successfully fetched and formatted tweets to {output_file}")
    else:
        log_error('Fetcher', "Failed to fetch and format tweets")
        sys.exit(1) 