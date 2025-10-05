#!/usr/bin/env python3
"""
Simplified fetcher module for Sumbird.
Uses utility classes and retry_utils for cleaner, more maintainable code.
"""
import os
import sys
from datetime import datetime

from config import (
    EXPORT_DIR, EXPORT_TITLE_FORMAT, HANDLES, NITTER_BASE_URL, 
    TIMEZONE, FETCHER_BATCH_SIZE, FETCHER_BATCH_DELAY,
    FETCHER_SESSION_MODE, FETCHER_REQUEST_DELAY
)
from utils.date_utils import get_date_range, get_date_str, get_target_date
from utils.feed_utils import FeedProcessor, BatchProcessor
from utils.file_utils import get_file_path
from utils.logging_utils import log_error, log_info, log_success
from utils.network_utils import NetworkClient, RateLimiter
from utils.session_utils import SessionManager


class SimplifiedFetcher:
    """Simplified fetcher using utility classes and retry_utils."""
    
    def __init__(self):
        # Initialize components
        self.network_client = NetworkClient(NITTER_BASE_URL)
        self.rate_limiter = RateLimiter()
        self.session_manager = SessionManager(
            mode=FETCHER_SESSION_MODE,
            base_delay=FETCHER_REQUEST_DELAY,
            batch_delay=FETCHER_BATCH_DELAY
        )
        self.feed_processor = FeedProcessor(
            self.network_client, 
            self.rate_limiter, 
            self.session_manager
        )
        self.batch_processor = BatchProcessor(
            self.feed_processor, 
            FETCHER_BATCH_SIZE
        )
    
    def get_feeds_from_handles(self):
        """Generate Nitter RSS feed URLs from Twitter handles."""
        feeds = []
        for handle in HANDLES:
            handle = handle.strip()
            if handle:
                feed_url = self.network_client.get_feed_url(handle)
                feed_title = f"@{handle}"
                feeds.append({
                    'url': feed_url,
                    'title': feed_title
                })
        return feeds
    
    def fetch_and_format(self):
        """Main function to fetch and format tweets."""
        # Get the target date
        target_date = get_target_date()
        date_str = get_date_str()
        
        # Generate output file path
        output_file = get_file_path('export', date_str)
        
        log_info('SimplifiedFetcher', f"Nitter Base URL: {NITTER_BASE_URL}")
        log_info('SimplifiedFetcher', f"Target date: {date_str}")
        log_info('SimplifiedFetcher', f"Session mode: {self.session_manager.mode}")
        
        # Get feeds and posts
        feeds = self.get_feeds_from_handles()
        feeds_total = len(feeds)
        
        log_info('SimplifiedFetcher', f"Processing {feeds_total} feeds with session-aware delays...")
        
        target_start, target_end = get_date_range(target_date)
        posts, feeds_success, failed_handles = self.batch_processor.process_feeds_in_batches(
            feeds, target_start, target_end
        )
        
        log_info('SimplifiedFetcher', f"Retrieved {len(posts)} posts from {feeds_success}/{feeds_total} feeds")
        
        # Log failed feeds summary if there are any failures
        if failed_handles:
            log_info('SimplifiedFetcher', f"Failed feeds summary:")
            for failed_feed in failed_handles:
                log_info('SimplifiedFetcher', f"- {failed_feed['handle']}: {failed_feed['reason']}")
        
        # Save to file
        self.save_to_file(posts, output_file, date_str)
        
        # Log completion
        log_success('SimplifiedFetcher', f"Successfully fetched and formatted tweets to {output_file}")
        
        return output_file, feeds_success, feeds_total, failed_handles
    
    def save_to_file(self, posts, output_file, date_str):
        """Save processed posts to output file."""
        if not posts:
            log_info('SimplifiedFetcher', "No posts found to save")
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
    """Module-level function for pipeline compatibility."""
    fetcher = SimplifiedFetcher()
    return fetcher.fetch_and_format()


def main():
    """Main function for standalone execution."""
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Create necessary directories when running as standalone
    if not os.path.exists(EXPORT_DIR):
        log_info('SimplifiedFetcher', f"Creating directory: {EXPORT_DIR}")
        os.makedirs(EXPORT_DIR, exist_ok=True)
    
    # Initialize and run fetcher
    fetcher = SimplifiedFetcher()
    output_file, feeds_success, feeds_total, failed_handles = fetcher.fetch_and_format()
    
    if output_file and os.path.exists(output_file):
        log_success('SimplifiedFetcher', f"Successfully fetched and formatted tweets to {output_file}")
    else:
        log_error('SimplifiedFetcher', "Failed to fetch and format tweets")
        sys.exit(1)


if __name__ == "__main__":
    main()
