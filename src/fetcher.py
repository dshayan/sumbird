#!/usr/bin/env python3
"""
Module for fetching RSS feeds from Twitter/X via self-hosted Nitter and formatting them.
This module can be run independently or as part of the pipeline.
"""
import os
import sys
from datetime import datetime

# Import utilities from utils package
from utils.date_utils import (
    get_target_date, get_date_str, 
    get_date_range, convert_to_timezone, format_feed_datetime
)
from utils.file_utils import get_file_path
from utils.html_utils import strip_html, clean_text
from utils.logging_utils import log_error, log_info, log_success, log_warning
from utils.retry_utils import with_retry_sync

# Import configuration
from config import (
    HANDLES, TIMEZONE, EXPORT_DIR, EXPORT_TITLE_FORMAT,
    RSS_TIMEOUT, RETRY_MAX_ATTEMPTS
)

# Import feedparser directly, no patching needed
import feedparser

# Nitter configuration
NITTER_BASE_URL = "http://localhost:8080"

def convert_to_x_url(url):
    """Convert Nitter URL to x.com format.
    
    Args:
        url (str): Original Nitter URL
        
    Returns:
        str: Converted x.com URL
    """
    if not url:
        return url
    
    # Convert localhost Nitter URLs to x.com format
    if 'localhost' in url and '/status/' in url:
        # Extract username and status ID from the URL
        if 'localhost:8080' in url:
            url_parts = url.split('localhost:8080/')
        else:
            url_parts = url.split('localhost/')
        
        if len(url_parts) > 1:
            path = url_parts[1]
            if '/status/' in path:
                username = path.split('/status/')[0]
                status_id = path.split('/status/')[1].split('#')[0]
                return f"https://x.com/{username}/status/{status_id}"
    
    return url

def get_feeds_from_handles():
    """Generate Nitter RSS feed URLs from Twitter handles."""
    feeds = []
    for handle in HANDLES:
        handle = handle.strip()
        if handle:
            # Use Nitter RSS feeds
            feed_url = f"{NITTER_BASE_URL}/{handle}/rss"
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
                # Only log individual failures, not successes
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
                    
                    # Get content from description or summary
                    content = entry.get('description', '') or entry.get('summary', '')
                    
                    # Clean HTML from content
                    content = strip_html(content)
                    content = clean_text(content)
                    
                    # Handle retweets - convert Nitter retweet format to x.com format
                    if is_retweet and url:
                        # Extract original author from the URL
                        original_author = "unknown"
                        if 'localhost:8080' in url:
                            url_parts = url.split('localhost:8080/')
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
    """
    Analyze why a feed failed and return a descriptive reason.
    
    Args:
        parsed_feed: The feedparser result object
        feed_handle: The handle being processed (e.g., "@username")
        
    Returns:
        str: Descriptive failure reason
    """
    # Check for common failure patterns
    if not hasattr(parsed_feed, 'feed') or parsed_feed.feed is None:
        return "No feed data received (possible network issue or invalid URL)"
    
    if hasattr(parsed_feed, 'bozo') and parsed_feed.bozo:
        if hasattr(parsed_feed, 'bozo_exception'):
            return f"Feed parsing error: {str(parsed_feed.bozo_exception)}"
        else:
            return "Feed parsing error (malformed XML/RSS)"
    
    if hasattr(parsed_feed, 'status'):
        if parsed_feed.status == 404:
            return "Feed not found (404) - account may not exist or be private"
        elif parsed_feed.status == 403:
            return "Access forbidden (403) - account may be private or restricted"
        elif parsed_feed.status == 429:
            return "Rate limited (429) - too many requests"
        elif parsed_feed.status >= 500:
            return f"Server error ({parsed_feed.status}) - service unavailable"
        elif parsed_feed.status != 200:
            return f"HTTP error ({parsed_feed.status})"
    
    if hasattr(parsed_feed, 'entries') and len(parsed_feed.entries) == 0:
        return "Feed is empty (no entries found)"
    
    # Check for specific error messages in the feed
    if hasattr(parsed_feed.feed, 'title'):
        title = parsed_feed.feed.title.lower()
        if 'error' in title or 'not found' in title:
            return f"Feed error: {parsed_feed.feed.title}"
    
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
    
    log_info('Fetcher', f"Nitter Base URL: {NITTER_BASE_URL}")
    log_info('Fetcher', f"Target date: {date_str}")
    
    # Get feeds and posts
    feeds = get_feeds_from_handles()
    feeds_total = len(feeds)
    
    log_info('Fetcher', f"Processing {feeds_total} feeds...")
    
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
