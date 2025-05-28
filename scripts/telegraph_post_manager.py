#!/usr/bin/env python3
"""
Telegraph Post Manager - Combines listing and deletion of Telegraph posts.
"""
import os
import sys
import re
import json
import httpx
from datetime import datetime

# Add the parent directory to the path so we can import from the main project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    TIMEZONE, TELEGRAPH_ACCESS_TOKEN
)
from utils.date_utils import DATE_FORMAT, format_log_datetime, get_now

# Constants
TELEGRAPH_API_URL = "https://api.telegra.ph"
POSTS_FILE = os.path.join("logs", f"telegraph_posts_{get_now().strftime(DATE_FORMAT)}.txt")


def get_account_info():
    """Get information about the Telegraph account."""
    url = f"{TELEGRAPH_API_URL}/getAccountInfo"
    params = {
        "access_token": TELEGRAPH_ACCESS_TOKEN,
        "fields": '["short_name", "author_name", "auth_url", "page_count"]'
    }
    
    try:
        response = httpx.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


def get_page_list(offset=0, limit=50):
    """Get a list of pages belonging to the Telegraph account."""
    url = f"{TELEGRAPH_API_URL}/getPageList"
    params = {
        "access_token": TELEGRAPH_ACCESS_TOKEN,
        "offset": offset,
        "limit": limit
    }
    
    try:
        response = httpx.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


def get_page_content(path):
    """Get the content of a Telegraph page."""
    url = f"{TELEGRAPH_API_URL}/getPage"
    params = {
        "path": path,
        "return_content": True
    }
    
    try:
        response = httpx.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred when fetching content: {e}")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        print(f"An error occurred when fetching content: {e}")
        return {"ok": False, "error": str(e)}


def extract_path_from_url(url):
    """Extract the path from a Telegraph URL."""
    pattern = r"https?://(?:www\.)?telegra\.ph/([a-zA-Z0-9-_]+)"
    match = re.match(pattern, url)
    
    if match:
        return match.group(1)
    return None


def delete_post(url_or_path):
    """Delete a Telegraph post by emptying its content.
    
    Note: Telegraph API does not support unpublishing posts or setting is_published to false.
    This function performs a 'soft delete' by replacing the content with a deletion notice.
    """
    path = extract_path_from_url(url_or_path)
    
    if not path:
        print(f"Invalid URL or path: {url_or_path}")
        return
    
    try:
        # First get the current page to preserve the title
        response = httpx.get(
            f"{TELEGRAPH_API_URL}/getPage/{path}",
            params={"return_content": "true"}
        )
        
        if response.status_code != 200:
            print(f"Error getting page: {response.status_code}")
            return
        
        data = response.json()
        if not data.get("ok"):
            print(f"Error getting page: {data.get('error', 'Unknown error')}")
            return
        
        # Keep the original title but clear the content
        title = data["result"]["title"]
        
        # Minimal deletion notice content that satisfies Telegraph API requirements
        minimal_content = json.dumps([{"tag": "p", "children": ["This content has been deleted."]}])
        
        # Edit the page to replace content with deletion notice
        response = httpx.post(
            f"{TELEGRAPH_API_URL}/editPage/{path}",
            params={
                "access_token": TELEGRAPH_ACCESS_TOKEN,
                "title": "Deleted",
                "content": minimal_content,
                "return_content": "true"
            }
        )
        
        if response.status_code != 200:
            print(f"Error deleting post: {response.status_code}")
            return
        
        data = response.json()
        if data.get("ok"):
            print(f"Successfully deleted post: {title}")
            return True
        else:
            print(f"Error deleting post: {data.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"Exception occurred while deleting post: {e}")
        return False


def extract_text_content(content_json):
    """Extract text content from Telegraph's content JSON format."""
    if not content_json or not isinstance(content_json, list):
        return "Content unavailable"
    
    result = []
    
    def process_node(node):
        if isinstance(node, str):
            result.append(node)
        elif isinstance(node, dict):
            if "children" in node and isinstance(node["children"], list):
                for child in node["children"]:
                    process_node(child)
            # Handle special nodes like images
            elif node.get("tag") == "img" and "attrs" in node:
                attrs = node.get("attrs", {})
                if "src" in attrs:
                    result.append(f"[Image: {attrs.get('src')}]")
    
    for node in content_json:
        process_node(node)
    
    return " ".join(result)


def list_posts(verbose=True):
    """List all Telegraph posts and return them."""
    if verbose:
        print("\nFetching account information...")
    
    account_info = get_account_info()
    
    if not account_info.get("ok"):
        print(f"Error fetching account info: {account_info.get('error')}")
        sys.exit(1)
    
    total_pages = account_info["result"].get("page_count", 0)
    
    if verbose:
        print(f"Found {total_pages} posts associated with this account.")
    
    if total_pages == 0:
        if verbose:
            print("No posts found.")
        return []
    
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(POSTS_FILE), exist_ok=True)
    
    # Fetch all pages
    all_pages = []
    offset = 0
    limit = 50  # Telegraph API allows max 50 per request
    
    while offset < total_pages:
        if verbose:
            print(f"Fetching pages {offset+1}-{min(offset+limit, total_pages)} of {total_pages}...")
        
        result = get_page_list(offset, limit)
        
        if not result.get("ok"):
            print(f"Error fetching page list: {result.get('error')}")
            sys.exit(1)
        
        all_pages.extend(result["result"]["pages"])
        offset += limit
    
    # Sort pages by date (newest first)
    all_pages.sort(key=lambda x: x.get("created", 0), reverse=True)
    
    # Write to output file
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        f.write(f"TELEGRAPH POSTS REPORT - Generated on {format_log_datetime(get_now())}\n")
        f.write(f"Account: {account_info['result'].get('author_name', 'Unknown')} ({account_info['result'].get('short_name', 'Unknown')})\n")
        f.write(f"Total Posts: {total_pages}\n\n")
        f.write(f"{'=' * 80}\n\n")
        
        for page in all_pages:
            title = page.get('title', 'Untitled')
            path = page.get('path', '')
            url = f"https://telegra.ph/{path}"
            views = page.get("views", 0)
            author_name = page.get("author_name", "Unknown")
            
            f.write(f"Title: {title}\n")
            f.write(f"Author: {author_name}\n")
            f.write(f"Views: {views}\n")
            f.write(f"URL: {url}\n")
            f.write("\n")
    
    if verbose:
        print(f"Report saved to {POSTS_FILE}")
        print(f"Total posts found: {len(all_pages)}")
        
        # Display posts to the user
        print("\n===== POST LIST =====")
        for i, page in enumerate(all_pages, 1):
            title = page.get('title', 'Untitled')
            url = f"https://telegra.ph/{page.get('path', '')}"
            views = page.get("views", 0)
            
            print(f"\n{i}. {title}")
            print(f"   URL: {url}")
            print(f"   Views: {views}")
    
    return all_pages


def main():
    """Main function to manage Telegraph posts."""
    print("TELEGRAPH POST MANAGER")
    print("=====================")
    print("This tool allows you to list and delete posts from your Telegraph account.")
    
    try:
        while True:
            posts = list_posts()
            
            if not posts:
                print("No posts to manage. Exiting.")
                break
            
            delete_choice = input("\nWould you like to delete a post? (y/n): ").strip().lower()
            
            if delete_choice != 'y':
                print("No posts will be deleted. Exiting.")
                break
            
            print("\nEnter the URL of the post you want to delete.")
            url = input("URL (or 'q' to quit): ").strip()
            
            if url.lower() in ('q', 'quit', 'exit'):
                print("Operation cancelled. Exiting.")
                break
            
            path = extract_path_from_url(url)
            
            if not path:
                print("Error: Invalid Telegraph URL. Please enter a valid URL.")
                continue
            
            success = delete_post(url)
            
            if success:
                print(f"✅ Post deleted successfully")
                print(f"[{format_log_datetime(get_now())}] SUCCESS - Deleted: {url}")
            else:
                print(f"❌ Failed to delete post")
                print(f"[{format_log_datetime(get_now())}] FAILED - Could not delete: {url}")
            
            continue_choice = input("\nWould you like to continue managing posts? (y/n): ").strip().lower()
            
            if continue_choice != 'y':
                print("\nUpdating post list report before exiting...")
                list_posts(verbose=False)
                print(f"Report updated at {POSTS_FILE}")
                print("Exiting.")
                break
    
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user. Exiting safely.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        print("\nTelegraph Post Manager session ended.")


if __name__ == "__main__":
    main() 