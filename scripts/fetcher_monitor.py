#!/usr/bin/env python3
"""
Script to capture the complete HTTP headers, request, and response that fetcher.py makes.
This captures the actual HTTP traffic that feedparser generates without interfering.
"""
import os
import sys
import json
import requests
import feedparser
from datetime import datetime
import urllib.request
import urllib.error
import http.client

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BASE_URL

# Global variable to store captured requests
captured_requests = []

def patch_http_client():
    """Patch the HTTP client to capture complete HTTP traffic without interfering."""
    global captured_requests
    captured_requests = []
    
    # Store original HTTPConnection methods
    original_HTTPConnection_request = http.client.HTTPConnection.request
    original_HTTPSConnection_request = http.client.HTTPSConnection.request
    original_HTTPConnection_getresponse = http.client.HTTPConnection.getresponse
    original_HTTPSConnection_getresponse = http.client.HTTPSConnection.getresponse
    
    def patched_HTTPConnection_request(self, method, url, body=None, headers=None, **kwargs):
        """Patched HTTPConnection.request that captures request details."""
        
        # Capture request details
        request_data = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'url': url,
            'headers': dict(headers) if headers else {},
            'body': body.decode('utf-8') if body else None,
            'host': self.host,
            'port': self.port,
            'protocol': 'HTTPS' if isinstance(self, http.client.HTTPSConnection) else 'HTTP'
        }
        
        # Store request data for later use
        self._captured_request_data = request_data
        
        try:
            # Call original method
            if isinstance(self, http.client.HTTPSConnection):
                result = original_HTTPSConnection_request(self, method, url, body, headers, **kwargs)
            else:
                result = original_HTTPConnection_request(self, method, url, body, headers, **kwargs)
            
            return result
            
        except Exception as e:
            request_data['error'] = str(e)
            captured_requests.append(request_data)
            raise
    
    def patched_HTTPConnection_getresponse(self, *args, **kwargs):
        """Patched getresponse to capture response data without interfering."""
        try:
            # Get the original response
            if isinstance(self, http.client.HTTPSConnection):
                response = original_HTTPSConnection_getresponse(self, *args, **kwargs)
            else:
                response = original_HTTPConnection_getresponse(self, *args, **kwargs)
            
            # If we have captured request data, just capture basic response info
            if hasattr(self, '_captured_request_data'):
                try:
                    # Capture response metadata without reading the body
                    response_data = {
                        'status_code': response.status,
                        'response_headers': dict(response.headers),
                        'reason': response.reason,
                        'version': response.version
                    }
                    
                    self._captured_request_data.update(response_data)
                    captured_requests.append(self._captured_request_data)
                    
                except Exception as e:
                    self._captured_request_data['response_error'] = str(e)
                    captured_requests.append(self._captured_request_data)
            
            return response
            
        except Exception as e:
            if hasattr(self, '_captured_request_data'):
                self._captured_request_data['response_error'] = str(e)
                captured_requests.append(self._captured_request_data)
            raise
    
    # Apply the patches
    http.client.HTTPConnection.request = patched_HTTPConnection_request
    http.client.HTTPSConnection.request = patched_HTTPConnection_request
    http.client.HTTPConnection.getresponse = patched_HTTPConnection_getresponse
    http.client.HTTPSConnection.getresponse = patched_HTTPConnection_getresponse
    
    print("🔍 HTTP client patched for complete traffic capture")

def run_fetcher_for_handle(handle="OpenAI"):
    """Run fetcher.py code for a single handle using the exact same date logic as fetcher.py."""
    
    try:
        # Import fetcher functions
        from src.fetcher import get_feeds_from_handles, get_posts
        from utils.date_utils import get_target_date, get_date_range, get_date_str
        
        print(f"🚀 Running fetcher.py code for handle: @{handle}")
        print(f"📍 Base URL: {BASE_URL}")
        
        # Use EXACT same date logic as fetcher.py
        target_date = get_target_date()  # Uses yesterday by default or TARGET_DATE env var
        date_str = get_date_str()        # Same date string format as fetcher.py
        target_start, target_end = get_date_range(target_date)
        
        print(f"📅 Target date: {date_str} (from config/env)")
        print(f"⏰ Date range: {target_start} to {target_end}")
        
        # Create a custom feeds list with just one handle
        custom_feeds = [{
            'url': f"{BASE_URL}{handle}/rss",
            'title': f"@{handle}"
        }]
        
        # Run the actual fetcher code with the same date range
        posts, feeds_success, failed_handles = get_posts(custom_feeds, target_start, target_end)
        
        print(f"✅ Fetcher completed")
        print(f"📊 Feeds successful: {feeds_success}")
        print(f"📝 Posts found: {len(posts)}")
        
        if posts:
            print(f"📄 First post: {posts[0]['content'][:100]}...")
        
        return posts, date_str
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def main():
    """Main function."""
    # You can change this handle to any Twitter handle you want to test
    handle = "OpenAI"
    
    print(f"🎯 Capturing complete HTTP traffic for handle: @{handle}")
    print(f"📍 Base URL: {BASE_URL}")
    print()
    
    # Patch HTTP client
    patch_http_client()
    
    # Run fetcher with same date logic as fetcher.py
    posts, date_str = run_fetcher_for_handle(handle)
    
    # Save log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = f"logs/http_capture_{handle}_{timestamp}.json"
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Save captured requests
    try:
        log_data = {
            'handle': handle,
            'base_url': BASE_URL,
            'target_date': date_str,  # Include the actual target date from config/env
            'timestamp': datetime.now().isoformat(),
            'total_requests': len(captured_requests),
            'fetcher_success': posts is not None and len(posts) > 0,
            'posts_found': len(posts) if posts else 0,
            'requests': captured_requests
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Log saved to: {log_file}")
        
    except Exception as e:
        print(f"❌ Error saving log: {e}")
    
    print(f"\n📊 Summary:")
    print(f"   - Target date (from config/env): {date_str}")
    print(f"   - HTTP requests captured: {len(captured_requests)}")
    print(f"   - Fetcher success: {posts is not None and len(posts) > 0}")
    print(f"   - Posts found: {len(posts) if posts else 0}")
    print(f"   - Log file: {log_file}")
    
    if posts:
        print(f"   - First post: {posts[0]['content'][:50]}...")
    
    print(f"\n✅ Done! HTTP traffic captured using the same date as fetcher.py!")

if __name__ == "__main__":
    main()
