#!/usr/bin/env python3
"""
Module for fetching RSS feeds from Twitter/X and formatting them.
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
from utils.logging_utils import log_error

# Import configuration
from config import BASE_URL, HANDLES, TIMEZONE, EXPORT_DIR, EXPORT_TITLE_FORMAT

# Import feedparser directly, no patching needed
import feedparser

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

def get_posts(feeds, target_start, target_end):
    """Fetch posts from feeds within the specified date range."""
    results = []
    successful_feeds = 0
    failed_handles = []
    
    for feed in feeds:
        try:
            print(f"Fetching: {feed['title']} from {feed['url']}")
            parsed_feed = feedparser.parse(feed['url'])
            
            if parsed_feed.feed and hasattr(parsed_feed.feed, 'title'):
                feed['title'] = parsed_feed.feed.title
                successful_feeds += 1
            else:
                handle = feed['title'].replace('@', '')
                failed_handles.append(handle)
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
                    content = None
                    
                    if hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].value
                    else:
                        content = entry.title
                    
                    content = strip_html(content)
                    content = clean_text(content)
                    
                    results.append({
                        'source': feed['title'],
                        'content': content,
                        'date': format_feed_datetime(pub_date),
                        'timestamp': pub_date
                    })
        except Exception as e:
            log_error('Fetcher', f"Error fetching {feed['url']}", e)
            handle = feed['title'].replace('@', '')
            failed_handles.append(handle)
    
    results.sort(key=lambda x: x['timestamp'])
    return results, successful_feeds, failed_handles

def save_to_file(posts, output_file, date_str):
    """Save processed posts to output file."""
    if not posts:
        print("No posts found to save")
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
                    f.write(f"- {post['time']}: {post['content']}\n")
                
                f.write("\n")

def fetch_and_format():
    """Main function to fetch and format tweets."""
    # Get the target date
    target_date = get_target_date()
    date_str = get_date_str()
    
    # Generate output file path using the centralized function
    output_file = get_file_path('export', date_str)
    
    print(f"Base URL: {BASE_URL}")
    print(f"Handles to process: {', '.join(HANDLES)}")
    print(f"Target date: {date_str}")
    
    # Get feeds and posts
    feeds = get_feeds_from_handles()
    feeds_total = len(feeds)
    
    target_start, target_end = get_date_range(target_date)
    posts, feeds_success, failed_handles = get_posts(feeds, target_start, target_end)
    
    print(f"Retrieved {len(posts)} posts from {feeds_success}/{feeds_total} feeds")
    
    # Save to file
    save_to_file(posts, output_file, date_str)
    
    return output_file, feeds_success, feeds_total, failed_handles

if __name__ == "__main__":
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(EXPORT_DIR):
        print(f"Creating directory: {EXPORT_DIR}")
        os.makedirs(EXPORT_DIR, exist_ok=True)
    
    output_file, feeds_success, feeds_total, failed_handles = fetch_and_format()
    if output_file and os.path.exists(output_file):
        print(f"Successfully fetched and formatted tweets to {output_file}")
    else:
        print("Failed to fetch and format tweets")
        sys.exit(1) 