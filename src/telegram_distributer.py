#!/usr/bin/env python3
"""
Module for distributing content to Telegram channels.
This module can be run independently or as part of the pipeline.
"""
import json
import os
import re
from datetime import datetime

import httpx

from config import (
    FILE_FORMAT, GEMINI_API_KEY, GEMINI_TELEGRAM_MODEL,
    HEADLINE_WRITER_PROMPT_PATH, PUBLISHED_DIR, RETRY_MAX_ATTEMPTS,
    TELEGRAM_AUDIO_TITLE_EN, TELEGRAM_AUDIO_TITLE_FA, TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_DISPLAY, TELEGRAM_CHAT_ID, TELEGRAM_DISABLE_WEB_PREVIEW,
    TELEGRAM_FILE_TIMEOUT, TELEGRAM_MESSAGE_TIMEOUT, TELEGRAM_MESSAGE_TITLE_FORMAT,
    TELEGRAM_PARSE_MODE, TIMEZONE, format_iso_datetime, get_date_str,
    get_file_path
)
from utils.file_utils import file_exists, get_audio_file_path, read_file
from utils.gemini_utils import create_gemini_text_client
from utils.html_utils import html_to_text
from utils.json_utils import read_json, write_json
from utils.logging_utils import handle_request_error, log_error, log_info, log_success
from utils.prompt_utils import load_prompt
from utils.retry_utils import with_retry_sync

class HeadlineGenerator:
    """Client for generating headlines using Gemini API."""
    
    def __init__(self, api_key, model, prompt_path):
        """Initialize the Gemini client for headline generation.
        
        Args:
            api_key (str): The Gemini API key
            model (str): The model to use for headline generation
            prompt_path (str): Path to the headline writer prompt file
        """
        self.client = create_gemini_text_client(
            api_key=api_key,
            model=model
        )
        
        # Load headline writer prompt
        self.prompt = load_prompt(
            prompt_path, 
            default="Create a concise headline from the following AI news summary:"
        )

    def generate_headline(self, summary_content):
        """Generate a headline from summary content with retry logic.
        
        Args:
            summary_content (str): The AI summary content
            
        Returns:
            tuple: (headline, input_tokens, output_tokens)
            
        Raises:
            Exception: If headline generation fails after all retries
        """
        # Create the prompt with the summary content
        full_prompt = f"{self.prompt}\n\n{summary_content}"
        
        # Generate headline using the centralized Gemini client
        result = self.client.generate_text(full_prompt)
        if isinstance(result, tuple):
            # Return the full tuple (text, input_tokens, output_tokens)
            return result
        else:
            # Fallback for backward compatibility
            return result, 0, 0

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

@with_retry_sync(timeout=TELEGRAM_MESSAGE_TIMEOUT, max_attempts=RETRY_MAX_ATTEMPTS)
def send_telegram_channel_post(content, chat_id):
    """Send a post to a Telegram channel with retry logic.
    
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
            timeout=TELEGRAM_MESSAGE_TIMEOUT
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

@with_retry_sync(timeout=TELEGRAM_FILE_TIMEOUT, max_attempts=RETRY_MAX_ATTEMPTS)
def send_telegram_audio_group(audio_files, chat_id):
    """Send multiple audio files as a media group to a Telegram channel with retry logic.
    
    Args:
        audio_files (list): List of dicts with 'path' and 'title' keys
        chat_id (str): Channel ID
    
    Returns:
        tuple: (success, message_url) where success is a boolean and message_url is a string or empty
    """
    try:
        # Validate the chat ID format
        is_valid, error_message = validate_channel_id(chat_id)
        if not is_valid:
            log_error('TelegramDistributer', f"{error_message}\nReceived channel ID: '{chat_id}'")
            return False, ""
        
        # Check if all audio files exist
        for audio_file in audio_files:
            if not file_exists(audio_file['path']):
                log_error('TelegramDistributer', f"Audio file not found: {audio_file['path']}")
                return False, ""
        
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup"
        
        # Prepare media group
        media = []
        files = {}
        
        for i, audio_file in enumerate(audio_files):
            file_key = f"audio{i}"
            media.append({
                "type": "audio",
                "media": f"attach://{file_key}",
                "title": audio_file.get('title', ''),
                "parse_mode": TELEGRAM_PARSE_MODE
            })
            
            # Read file for upload
            with open(audio_file['path'], 'rb') as f:
                files[file_key] = (os.path.basename(audio_file['path']), f.read(), 'audio/mpeg')
        
        data = {
            'chat_id': chat_id,
            'media': json.dumps(media),
            'disable_notification': False
        }
        
        # Make the API request
        response = httpx.post(
            api_url,
            files=files,
            data=data,
            timeout=TELEGRAM_FILE_TIMEOUT
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            response_json = response.json()
            if response_json.get("ok"):
                # Extract message info to construct URL (use first message in the group)
                messages = response_json.get("result", [])
                if messages:
                    first_message = messages[0]
                    message_id = first_message.get("message_id")
                    chat_id_value = first_message.get("chat", {}).get("id")
                    chat_username = first_message.get("chat", {}).get("username")
                    
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
                    return True, ""
            else:
                return handle_request_error('TelegramDistributer', response, "Telegram API error"), ""
        else:
            return handle_request_error('TelegramDistributer', response, "API request failed"), ""
    
    except Exception as e:
        log_error('TelegramDistributer', f"Error sending Telegram audio group", e)
        return False, ""

@with_retry_sync(timeout=TELEGRAM_FILE_TIMEOUT, max_attempts=RETRY_MAX_ATTEMPTS)
def send_telegram_audio(audio_file_path, chat_id, title=""):
    """Send an audio file to a Telegram channel with retry logic.
    
    Args:
        audio_file_path (str): Path to the audio file
        chat_id (str): Channel ID
        title (str): Title for the audio file
    
    Returns:
        tuple: (success, message_url) where success is a boolean and message_url is a string or empty
    """
    try:
        # Validate the chat ID format
        is_valid, error_message = validate_channel_id(chat_id)
        if not is_valid:
            log_error('TelegramDistributer', f"{error_message}\nReceived channel ID: '{chat_id}'")
            return False, ""
        
        # Check if audio file exists
        if not file_exists(audio_file_path):
            log_error('TelegramDistributer', f"Audio file not found: {audio_file_path}")
            return False, ""
            
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
        
        # Prepare the files and data for multipart upload
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'audio': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg')
            }
            
            data = {
                'chat_id': chat_id,
                'title': title,
                'parse_mode': TELEGRAM_PARSE_MODE,
                'disable_notification': False
            }
            
            # Make the API request
            response = httpx.post(
                api_url,
                files=files,
                data=data,
                timeout=TELEGRAM_FILE_TIMEOUT
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
        log_error('TelegramDistributer', f"Error sending Telegram audio file", e)
        return False, ""

def format_telegram_post_with_headline(published_data, headline):
    """Format the published data into a Telegram post with provided headline.
    
    Args:
        published_data (dict): The published data
        headline (str): The generated headline
    
    Returns:
        dict: Formatted content for Telegram post
    """
    # Extract information from published data
    title = published_data.get("title", "AI Updates on " + published_data.get("source_date", ""))
    en_url = published_data.get("url", "")
    fa_url = published_data.get("fa_url", "")
    
    # Create the message title using the title format
    message = TELEGRAM_MESSAGE_TITLE_FORMAT.format(title=title) + "\n\n"
    
    # Add the generated headline
    message += headline + "\n\n"
    
    # Add the summary message with link(s) using the configured format
    if en_url and fa_url:
        # Both English and Persian URLs are available
        message += f"🇬🇧 <a href=\"{en_url}\">English Summary</a>\n🇮🇷 <a href=\"{fa_url}\">Persian Summary</a>"
    
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
        tuple: (success, message_url, input_tokens, output_tokens) where success is a boolean, 
               message_url is a string, and token counts are integers
    """
    # Get the date string
    date_str = get_date_str()
    
    # Generate file path using the centralized function
    published_file = get_file_path('published', date_str)
    
    # Check if published file exists
    if not os.path.exists(published_file):
        log_error('TelegramDistributer', f"Published file not found at {published_file}")
        return False, "", 0, 0
    
    try:
        # Read the published file
        published_data = read_json(published_file)
        
        # Check if both English and Persian URLs are available
        en_url = published_data.get("url", "")
        fa_url = published_data.get("fa_url", "")
        
        if not en_url:
            log_error('TelegramDistributer', "English summary URL not found in published data")
            return False, "", 0, 0
        
        if not fa_url:
            log_error('TelegramDistributer', "Persian summary URL not found in published data")
            return False, "", 0, 0
        
        # Check if both summary files exist
        summary_file = get_file_path('summary', date_str)
        translated_file = get_file_path('translated', date_str)
        
        if not file_exists(summary_file):
            log_error('TelegramDistributer', f"English summary file not found: {summary_file}")
            return False, "", 0, 0
        
        if not file_exists(translated_file):
            log_error('TelegramDistributer', f"Persian summary file not found: {translated_file}")
            return False, "", 0, 0
        
        # Generate headline from summary content (required, no fallback)
        summary_content = read_file(summary_file)
        if not summary_content:
            log_error('TelegramDistributer', f"Failed to read summary content from {summary_file}")
            return False, "", 0, 0
        
        # Convert HTML to plain text for headline generation
        summary_text = html_to_text(summary_content)
        if not summary_text.strip():
            log_error('TelegramDistributer', f"No text content found after HTML conversion from {summary_file}")
            return False, "", 0, 0
        
        # Initialize headline generator and generate headline
        try:
            headline_generator = HeadlineGenerator(GEMINI_API_KEY, GEMINI_TELEGRAM_MODEL, HEADLINE_WRITER_PROMPT_PATH)
            headline, input_tokens, output_tokens = headline_generator.generate_headline(summary_text)
        except Exception as e:
            log_error('TelegramDistributer', "Headline generation failed, cannot proceed without generated headline", e)
            return False, "", 0, 0
        
        # Format content for Telegram
        telegram_content = format_telegram_post_with_headline(published_data, headline)
        
        # Send the message
        channel_id = TELEGRAM_CHAT_ID
        success, message_url = send_telegram_channel_post(telegram_content, channel_id)
        
        if success:
            log_success('TelegramDistributer', f"Successfully distributed content to Telegram channel {channel_id}")
            
            # Check for audio files and send them as a group (optional - only if they exist)
            # Use the new function that checks for both MP3 and WAV
            summary_audio = get_audio_file_path('narrated', date_str)
            translated_audio = get_audio_file_path('narrated', date_str, lang='FA')
            
            audio_urls = []
            
            # Check if both audio files exist before attempting to send
            if file_exists(summary_audio) and file_exists(translated_audio):
                audio_files_to_send = [
                    {
                        'path': summary_audio,
                        'title': TELEGRAM_AUDIO_TITLE_EN
                    },
                    {
                        'path': translated_audio,
                        'title': TELEGRAM_AUDIO_TITLE_FA
                    }
                ]
                
                # Send audio files as a group
                log_info('TelegramDistributer', f"Sending {len(audio_files_to_send)} audio files as a group")
                audio_success, audio_url = send_telegram_audio_group(audio_files_to_send, channel_id)
                if audio_success:
                    log_success('TelegramDistributer', "Audio group sent successfully")
                    audio_urls.append(audio_url)
                else:
                    log_error('TelegramDistributer', "Failed to send audio group, but text message was sent successfully")
                    # Don't fail the entire distribution if audio fails
            else:
                # Audio files don't exist (likely --skip-tts was used)
                if not file_exists(summary_audio) and not file_exists(translated_audio):
                    log_info('TelegramDistributer', "Audio files not found - sending text message only (TTS steps may have been skipped)")
                elif not file_exists(summary_audio):
                    log_info('TelegramDistributer', f"Summary audio file not found: {summary_audio} - sending text message only")
                elif not file_exists(translated_audio):
                    log_info('TelegramDistributer', f"Translated audio file not found: {translated_audio} - sending text message only")
            
            # Update the published data with telegram distribution info
            published_data["telegram_distributed"] = {
                "timestamp": format_iso_datetime(),
                "channel": channel_id,
                "message_url": message_url,
                "audio_urls": audio_urls,
                "headline": headline
            }
            
            # Save the updated published data
            write_json(published_file, published_data)
            
            # Log completion and token usage
            log_success('TelegramDistributer', "Telegram distribution completed successfully")
            log_info('TelegramDistributer', f"Message URL: {message_url}")
            if audio_urls:
                log_info('TelegramDistributer', f"Audio URLs: {', '.join(audio_urls)}")
            log_info('TelegramDistributer', f"Tokens used: {input_tokens} input, {output_tokens} output")
            
            return True, message_url, input_tokens, output_tokens
        else:
            log_error('TelegramDistributer', "Failed to distribute to Telegram channel")
            return False, "", 0, 0
    
    except Exception as e:
        log_error('TelegramDistributer', f"Error distributing content", e)
        return False, "", 0, 0

if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    distribution_success, message_url, input_tokens, output_tokens = distribute()
    if distribution_success:
        log_success('TelegramDistributer', "Telegram distribution completed successfully")
        log_info('TelegramDistributer', f"Message URL: {message_url}")
        log_info('TelegramDistributer', f"Tokens used: {input_tokens} input, {output_tokens} output")
    else:
        log_error('TelegramDistributer', "Telegram distribution failed") 