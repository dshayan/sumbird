#!/usr/bin/env python3
"""
Feed processing utilities for Sumbird.
Handle RSS feed processing and data extraction.
"""
import random
import time
from datetime import datetime
from typing import Dict, List, Tuple

import feedparser

from utils.date_utils import convert_to_timezone, format_feed_datetime
from utils.html_utils import clean_text, strip_html
from utils.logging_utils import log_error, log_info, log_warning
from utils.retry_utils import with_retry_sync


def get_base_delay(min_delay: float = 8.0, max_delay: float = 12.0) -> float:
    """Get base delay with random jitter.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Random delay between min and max
    """
    return random.uniform(min_delay, max_delay)


def get_batch_delay(batch_delay: float, jitter: float = 15.0) -> float:
    """Get batch delay with random jitter.
    
    Args:
        batch_delay: Base batch delay in seconds
        jitter: Maximum random jitter to add
        
    Returns:
        Batch delay with added jitter
    """
    return batch_delay + random.uniform(0, jitter)


class FeedProcessor:
    """Handle feed processing logic with retry and error handling."""
    
    def __init__(self, network_client, rate_limiter, base_delay_min: float = 8.0, base_delay_max: float = 12.0):
        self.network_client = network_client
        self.rate_limiter = rate_limiter
        self.base_delay_min = base_delay_min
        self.base_delay_max = base_delay_max
    
    @with_retry_sync(max_attempts=3, module_name="FeedProcessor", context="feed processing")
    def process_feed(self, feed_url: str, feed_title: str) -> Tuple[feedparser.FeedParserDict, str]:
        """Process a single feed with retry logic.
        
        Args:
            feed_url (str): URL of the RSS feed
            feed_title (str): Human-readable feed title
            
        Returns:
            Tuple[feedparser.FeedParserDict, str]: Parsed feed and error message (if any)
        """
        try:
            # Apply rate limiting with random delay
            self.rate_limiter.wait_if_needed(get_base_delay(self.base_delay_min, self.base_delay_max))
            
            # Fetch the feed
            parsed_feed = self.network_client.fetch_feed(feed_url)
            
            # Validate feed
            if not self._is_valid_feed(parsed_feed):
                error_reason = self._analyze_feed_failure(parsed_feed, feed_title)
                return parsed_feed, error_reason
            
            return parsed_feed, ""
            
        except Exception as e:
            error_reason = f"Exception: {str(e)}"
            log_error('FeedProcessor', f"Failed to process feed {feed_title}: {e}")
            return None, error_reason
    
    def _is_valid_feed(self, parsed_feed: feedparser.FeedParserDict) -> bool:
        """Check if a feed is valid and has content.
        
        Args:
            parsed_feed: The feedparser result object
            
        Returns:
            bool: True if feed is valid, False otherwise
        """
        if not hasattr(parsed_feed, 'feed') or parsed_feed.feed is None:
            return False
        
        if hasattr(parsed_feed, 'bozo') and parsed_feed.bozo:
            return False
        
        if hasattr(parsed_feed, 'status') and parsed_feed.status != 200:
            return False
        
        if hasattr(parsed_feed, 'entries') and len(parsed_feed.entries) == 0:
            return False
        
        return True
    
    def _analyze_feed_failure(self, parsed_feed: feedparser.FeedParserDict, feed_handle: str) -> str:
        """Analyze why a feed failed and return a descriptive reason.
        
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
    
    def extract_posts(self, parsed_feed: feedparser.FeedParserDict, target_start: datetime, 
                      target_end: datetime, source: str) -> List[Dict]:
        """Extract posts from a parsed feed within the date range.
        
        Args:
            parsed_feed: Parsed RSS feed
            target_start: Start of target date range
            target_end: End of target date range
            source: Source name for the posts
            
        Returns:
            List[Dict]: List of extracted posts
        """
        posts = []
        
        for entry in parsed_feed.entries:
            pub_date = None
            
            # Convert time tuple to datetime and apply timezone
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                naive_dt = datetime(*entry.published_parsed[:6])
                pub_date = convert_to_timezone(naive_dt)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                naive_dt = datetime(*entry.updated_parsed[:6])
                pub_date = convert_to_timezone(naive_dt)
            else:
                continue
            
            # Check if post is within target date range
            if target_start <= pub_date < target_end:
                # Check if this is a retweet
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
                converted_url = self._convert_to_x_url(url)
                
                posts.append({
                    'source': source,
                    'content': content,
                    'url': converted_url,
                    'date': format_feed_datetime(pub_date),
                    'timestamp': pub_date
                })
        
        return posts
    
    def _convert_to_x_url(self, url: str) -> str:
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


class BatchProcessor:
    """Handle batch processing of feeds with session management."""
    
    def __init__(self, feed_processor: FeedProcessor, batch_size: int = 20, batch_delay: float = 30.0):
        self.feed_processor = feed_processor
        self.batch_size = batch_size
        self.batch_delay = batch_delay
    
    def process_feeds_in_batches(self, feeds: List[Dict], target_start: datetime, 
                                target_end: datetime) -> Tuple[List[Dict], int, List[Dict]]:
        """Process feeds in batches with session-aware delays.
        
        Args:
            feeds: List of feed dictionaries
            target_start: Start of target date range
            target_end: End of target date range
            
        Returns:
            Tuple[List[Dict], int, List[Dict]]: Posts, successful feeds count, failed handles
        """
        results = []
        successful_feeds = 0
        failed_handles = []
        
        # Shuffle feeds to avoid predictable patterns
        random.shuffle(feeds)
        
        # Process feeds in smaller batches to prevent session exhaustion
        batches = [feeds[i:i + self.batch_size] for i in range(0, len(feeds), self.batch_size)]
        
        log_info('BatchProcessor', f"Processing {len(feeds)} feeds in {len(batches)} batches of {self.batch_size}")
        
        for batch_num, batch in enumerate(batches):
            log_info('BatchProcessor', f"Processing batch {batch_num + 1}/{len(batches)} ({len(batch)} feeds)")
            
            # Add delay between batches to allow session recovery
            if batch_num > 0:
                delay = get_batch_delay(self.batch_delay)
                log_info('BatchProcessor', f"Waiting {delay:.1f}s between batches for session recovery...")
                time.sleep(delay)
            
            # Process each feed in the batch
            for i, feed in enumerate(batch):
                feed_handle = feed['title']  # e.g., "@username"
                
                # Log progress every 5 feeds within batch
                if i % 5 == 0:
                    log_info('BatchProcessor', f"Batch {batch_num + 1}: Processing feed {i+1}/{len(batch)}: {feed_handle}")
                
                try:
                    # Process the feed
                    parsed_feed, error_reason = self.feed_processor.process_feed(feed['url'], feed['title'])
                    
                    if error_reason:
                        # Feed failed
                        handle = feed['title'].replace('@', '')
                        failed_handles.append({'handle': handle, 'reason': error_reason})
                        continue
                    
                    # Feed was successful
                    successful_feeds += 1
                    
                    # Extract posts from the feed
                    posts = self.feed_processor.extract_posts(parsed_feed, target_start, target_end, feed['title'])
                    results.extend(posts)
                    
                except Exception as e:
                    # This catches exceptions that weren't handled by the retry mechanism
                    failure_reason = f"Exception: {str(e)}"
                    handle = feed['title'].replace('@', '')
                    failed_handles.append({'handle': handle, 'reason': failure_reason})
        
        # Sort results by timestamp
        results.sort(key=lambda x: x['timestamp'])
        return results, successful_feeds, failed_handles
