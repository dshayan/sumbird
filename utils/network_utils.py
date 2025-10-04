#!/usr/bin/env python3
"""
Network utilities for Sumbird.
Centralized network operations with retry and rate limiting.
"""
import random
import time
from typing import Dict, List, Optional

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.logging_utils import log_error, log_info, log_warning
from utils.retry_utils import with_retry_sync


class NetworkClient:
    """Centralized network client with retry and rate limiting."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        self.consecutive_429_errors = 0
        self.last_429_time = 0
    
    def _create_session(self):
        """Create a session with proper retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy for rate limits and server errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get randomized headers for requests."""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1'
        }
    
    @with_retry_sync(timeout=30, max_attempts=3, context="RSS feed fetch")
    def fetch_feed(self, feed_url: str) -> feedparser.FeedParserDict:
        """Fetch RSS feed with automatic retry and error handling.
        
        Args:
            feed_url (str): URL of the RSS feed to fetch
            
        Returns:
            feedparser.FeedParserDict: Parsed feed data
            
        Raises:
            requests.exceptions.RequestException: If fetch fails after retries
        """
        try:
            response = self.session.get(
                feed_url, 
                headers=self._get_headers(), 
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                self._handle_rate_limit()
                # Let retry_utils handle the retry
                raise requests.exceptions.RequestException("Rate limited")
            
            # Check for other rate limit indicators
            if 'x-rate-limit-remaining' in response.headers:
                remaining = int(response.headers.get('x-rate-limit-remaining', '1000'))
                if remaining < 50:
                    log_warning('NetworkClient', f"Low rate limit remaining: {remaining}")
                    time.sleep(random.uniform(10, 20))
            
            response.raise_for_status()
            
            # Parse with feedparser
            parsed_feed = feedparser.parse(response.content)
            
            # Reset error counters on success
            if response.status_code != 429:
                self.consecutive_429_errors = 0
            
            return parsed_feed
            
        except requests.exceptions.RequestException as e:
            log_error('NetworkClient', f"Request failed: {e}")
            raise
    
    def _handle_rate_limit(self):
        """Handle rate limiting with exponential backoff."""
        self.consecutive_429_errors += 1
        self.last_429_time = time.time()
        
        # Exponential backoff: 30s, 60s, 120s, etc.
        backoff_time = min(300, 30 * (2 ** (self.consecutive_429_errors - 1)))
        log_warning('NetworkClient', f"Rate limit hit, backing off for {backoff_time}s")
        time.sleep(backoff_time + random.uniform(5, 15))
    
    def get_feed_url(self, handle: str) -> str:
        """Generate feed URL for a Twitter handle.
        
        Args:
            handle (str): Twitter handle (with or without @)
            
        Returns:
            str: Full RSS feed URL
        """
        # Clean handle (remove @ if present)
        clean_handle = handle.lstrip('@')
        return f"{self.base_url}/{clean_handle}/rss"


class RateLimiter:
    """Simplified rate limiter for network requests."""
    
    def __init__(self, max_requests: int = 800, window_minutes: int = 15):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests = []
        self.last_request_time = 0
    
    def wait_if_needed(self, base_delay: float = 5.0):
        """Check if we need to wait before making a request.
        
        Args:
            base_delay (float): Base delay between requests in seconds
        """
        now = time.time()
        
        # Clean old requests outside current window
        window_start = now - (self.window_minutes * 60)
        self.requests = [req_time for req_time in self.requests if req_time > window_start]
        
        # Check if we need to wait due to rate limits
        if len(self.requests) >= self.max_requests:
            sleep_time = (self.window_minutes * 60) - (now % (self.window_minutes * 60))
            log_warning('RateLimiter', f"Rate limit reached, waiting {sleep_time:.1f}s")
            time.sleep(sleep_time + random.uniform(1, 3))
        
        # Apply base delay
        time_since_last = now - self.last_request_time
        if time_since_last < base_delay:
            remaining_delay = base_delay - time_since_last
            time.sleep(remaining_delay)
        
        # Record this request
        self.requests.append(now)
        self.last_request_time = now
