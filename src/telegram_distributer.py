#!/usr/bin/env python3
"""
Module for distributing content to Telegram channels.
This module can be run independently or as part of the pipeline.
"""
import os
import json
import httpx
from datetime import datetime
import re

from config import (
    PUBLISHED_DIR, FILE_FORMAT,
    get_date_str, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    TELEGRAM_MESSAGE_TITLE_FORMAT, TELEGRAM_SUMMARY_FORMAT,
    TELEGRAM_CHANNEL_DISPLAY, TELEGRAM_PARSE_MODE, TELEGRAM_DISABLE_WEB_PREVIEW,
    get_file_path, TIMEZONE, format_iso_datetime
)
from utils.logging_utils import log_error, handle_request_error

def validate_channel_id(channel_id):
    """Validates that the channel ID is in a proper format.
    
    Args:
        channel_id (str): The channel ID to validate
    
    Returns:
        tuple: (is_valid, error_message) where is_valid is a boolean and error_message is a string or None
    """
    # For public channels: should start with @
    if channel_id.startswith('@'):
        return True, None
    
    # For private channels: should be numeric, often starts with -100
    if channel_id.startswith('-100') and channel_id[4:].isdigit():
        return True, None
    
    # Simpler private channels/groups might just start with '-'
    if channel_id.startswith('-') and channel_id[1:].isdigit():
        return True, None
    
    # User IDs are just numeric
    if channel_id.isdigit():
        return True, None
    
    return False, (
        "Invalid channel ID format. Should be either:\n"
        "- For public channels: Start with @ (e.g., @channelname)\n"
        "- For private channels: Numeric ID (e.g., -1001234567890 or -123456789)\n"
        "- For users: Just numeric ID"
    )

def send_telegram_channel_post(content, chat_id):
    """Send a post to a Telegram channel.
    
    Args:
        content (dict): Content to post including text and optional parameters
        chat_id (str): Channel ID (should start with @ for public channels)
    
    Returns:
        tuple: (success, message_url) where success is a boolean and message_url is a string or empty
    """
    try:
        # Validate the chat ID format
        is_valid, error_message = validate_channel_id(chat_id)
        if not is_valid:
            log_error('TelegramDistributer', f"{error_message}\nReceived channel ID: '{chat_id}'")
            return False, ""
            
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Prepare the request data
        request_data = {
            "chat_id": chat_id,
            "text": content.get("text", ""),
            "parse_mode": content.get("parse_mode", TELEGRAM_PARSE_MODE),
            "disable_web_page_preview": content.get("disable_web_page_preview", TELEGRAM_DISABLE_WEB_PREVIEW),
            "disable_notification": content.get("disable_notification", False)
        }
        
        # Make the API request
        response = httpx.post(
            api_url,
            json=request_data,
            timeout=60
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get("ok"):
                # Extract message info to construct URL
                message_id = response_json.get("result", {}).get("message_id")
                chat_id_value = response_json.get("result", {}).get("chat", {}).get("id")
                chat_username = response_json.get("result", {}).get("chat", {}).get("username")
                
                # Construct message URL
                message_url = ""
                if chat_username:
                    # Public channel
                    message_url = f"https://t.me/{chat_username}/{message_id}"
                elif chat_id_value:
                    # Private channel
                    # Remove the minus sign if it's a negative ID
                    channel_id_str = str(chat_id_value)
                    if channel_id_str.startswith('-100'):
                        clean_id = channel_id_str[4:]  # Remove -100 prefix
                        message_url = f"https://t.me/c/{clean_id}/{message_id}"
                    elif channel_id_str.startswith('-'):
                        clean_id = channel_id_str[1:]  # Remove just the minus sign
                        message_url = f"https://t.me/c/{clean_id}/{message_id}"
                    else:
                        message_url = f"https://t.me/c/{channel_id_str}/{message_id}"
                
                return True, message_url
            else:
                return handle_request_error('TelegramDistributer', response, "Telegram API error"), ""
        else:
            return handle_request_error('TelegramDistributer', response, "API request failed"), ""
    
    except Exception as e:
        log_error('TelegramDistributer', "Error sending Telegram channel post", e)
        return False, ""

def format_telegram_post(published_data):
    """Format the published data into a Telegram post.
    
    Args:
        published_data (dict): The published data
    
    Returns:
        dict: Formatted content for Telegram post
    """
    # Extract information from published data
    title = published_data.get("title", "AI Updates on " + published_data.get("source_date", ""))
    en_url = published_data.get("url", "")
    fa_url = published_data.get("fa_url", "")
    
    # Get the number of successfully fetched sources
    # First check if we have it in published_data
    feeds_success = published_data.get("feeds_success", 0)
    
    # Create the message title using the title format
    message = TELEGRAM_MESSAGE_TITLE_FORMAT.format(title=title) + "\n\n"
    
    # Add the summary message with link(s) using the configured format
    if en_url:
        if fa_url:
            # Both English and Persian URLs are available
            message += TELEGRAM_SUMMARY_FORMAT.format(feeds_success=feeds_success, en_url=en_url, fa_url=fa_url)
        else:
            # Only English URL is available - fallback to using en_url as the only URL
            # Replace {fa_url} with {en_url} to handle environment configs without the updated format
            formatted_message = TELEGRAM_SUMMARY_FORMAT.replace("{fa_url}", "{en_url}")
            message += formatted_message.format(feeds_success=feeds_success, en_url=en_url)
        
    # Add the channel display at the end if it exists
    if TELEGRAM_CHANNEL_DISPLAY:
        message += "\n\n" + TELEGRAM_CHANNEL_DISPLAY
    
    return {
        "text": message,
        "parse_mode": TELEGRAM_PARSE_MODE,
        "disable_web_page_preview": TELEGRAM_DISABLE_WEB_PREVIEW
    }

def distribute():
    """Main function to distribute published content to Telegram channels.
    
    Returns:
        tuple: (success, message_url) where success is a boolean and message_url is a string
    """
    # Get the date string
    date_str = get_date_str()
    
    # Generate file path using the centralized function
    published_file = get_file_path('published', date_str)
    
    # Check if published file exists
    if not os.path.exists(published_file):
        log_error('TelegramDistributer', f"Published file not found at {published_file}")
        return False, ""
    
    try:
        # Read the published file
        with open(published_file, 'r', encoding='utf-8') as f:
            published_data = json.load(f)
        
        # Format content for Telegram
        telegram_content = format_telegram_post(published_data)
        
        # Get channel ID
        channel_id = TELEGRAM_CHAT_ID
        is_valid, error_message = validate_channel_id(channel_id)
        
        if not is_valid:
            log_error('TelegramDistributer', f"Warning: {error_message}. Will attempt to send with the provided ID: '{channel_id}'")
        
        # Send to Telegram channel
        success, message_url = send_telegram_channel_post(telegram_content, channel_id)
        if success:
            print(f"Successfully distributed content to Telegram channel {channel_id}")
            
            # Update the published data with telegram distribution info
            published_data["telegram_distributed"] = {
                "timestamp": format_iso_datetime(),
                "channel": channel_id,
                "message_url": message_url
            }
            
            # Save the updated published data
            with open(published_file, 'w', encoding='utf-8') as f:
                json.dump(published_data, f, ensure_ascii=False, indent=2)
            
            return True, message_url
        else:
            log_error('TelegramDistributer', "Failed to distribute to Telegram channel")
            return False, ""
    
    except Exception as e:
        log_error('TelegramDistributer', f"Error distributing content", e)
        return False, ""

if __name__ == "__main__":
    success, message_url = distribute()
    if success:
        print(f"Telegram distribution completed successfully")
        if message_url:
            print(f"Message URL: {message_url}")
    else:
        print("Telegram distribution failed") 