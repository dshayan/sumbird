#!/usr/bin/env python3
"""
Module for converting text content to speech using Gemini 2.5 Flash TTS.
This module can be run independently or as part of the pipeline.
"""
import os
import time
from pathlib import Path

from config import (
    GEMINI_API_KEY, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE, NARRATOR_PROMPT_PATH,
    SCRIPT_DIR, NARRATED_DIR, AUDIO_ARTIST, AUDIO_ALBUM, AUDIO_GENRE,
    TELEGRAM_AUDIO_TITLE_EN, TELEGRAM_AUDIO_TITLE_FA,
    get_date_str, get_file_path, AI_TIMEOUT
)
from utils.logging_utils import log_error, log_info, log_success
from utils.html_utils import html_to_text
from utils.file_utils import file_exists, read_file
from utils.gemini_utils import create_gemini_tts_client

def convert_html_to_text(html_content):
    """Convert HTML content to clean text for TTS.
    
    Args:
        html_content (str): HTML content to convert
        
    Returns:
        str: Clean text suitable for TTS
    """
    # Use the existing html_to_text utility
    text_content = html_to_text(html_content)
    
    # Additional cleaning for TTS
    # Remove markdown-style headers
    text_content = text_content.replace('# ', '').replace('## ', '').replace('### ', '')
    
    # Clean up any remaining formatting
    text_content = ' '.join(text_content.split())
    
    return text_content

def narrate_file(file_path, output_path, client, title=None, date_str=None):
    """Convert a single file to speech.
    
    Args:
        file_path (str): Path to the input file
        output_path (str): Path to save the audio file
        client (GeminiTTSClient): TTS client instance
        title (str, optional): Title for the audio file metadata
        date_str (str, optional): Date string for the audio file metadata
        
    Returns:
        str: Path to the created audio file, or None if failed
    """
    try:
        if not file_exists(file_path):
            log_error('Narrator', f"Input file not found: {file_path}")
            return None
        
        # Read the file content
        html_content = read_file(file_path)
        
        # Convert HTML to text
        text_content = convert_html_to_text(html_content)
        
        if not text_content.strip():
            log_error('Narrator', f"No text content found in {file_path}")
            return None
        
        log_info('Narrator', f"Processing {file_path}")
        log_info('Narrator', f"Text preview: {text_content[:200]}...")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convert to speech
        return client.text_to_speech(text_content, output_path, title, AUDIO_ARTIST, AUDIO_ALBUM, AUDIO_GENRE, date_str)
        
    except Exception as e:
        log_error('Narrator', f"Error processing file {file_path}", e)
        return None

def narrate():
    """Main function to convert summary and translated files to speech.
    
    Returns:
        tuple: (summary_audio_path, translated_audio_path) where paths are strings or None if failed
    """
    try:
        # Get the target date
        date_str = get_date_str()
        
        # Read the narrator prompt
        with open(NARRATOR_PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_template = f.read().strip()
        
        # Get file paths
        script_file = get_file_path('script', date_str)
        translated_script_file = get_file_path('script', date_str, lang='FA')
        
        # Verify both required files exist
        if not file_exists(script_file):
            log_error('Narrator', f"Required script file not found: {script_file}")
            return None, None
        
        if not file_exists(translated_script_file):
            log_error('Narrator', f"Required translated script file not found: {translated_script_file}")
            return None, None
        
        # Generate output paths
        summary_audio = get_file_path('narrated', date_str)
        translated_audio = get_file_path('narrated', date_str, lang='FA')
        
        summary_result = None
        translated_result = None
        
        # Check if summary audio already exists
        if file_exists(summary_audio):
            log_info('Narrator', f"Using existing summary audio: {summary_audio}")
            summary_result = summary_audio
        else:
            log_info('Narrator', "Converting Script to Speech")
            client = create_gemini_tts_client(
                api_key=GEMINI_API_KEY,
                model=GEMINI_TTS_MODEL,
                voice=GEMINI_TTS_VOICE,
                prompt_template=prompt_template,
                timeout=AI_TIMEOUT
            )
            summary_result = narrate_file(script_file, summary_audio, client, TELEGRAM_AUDIO_TITLE_EN, date_str)
            if summary_result:
                log_success('Narrator', f"Script audio created: {summary_result}")
            else:
                log_error('Narrator', "Failed to create required script audio")
                return None, None
        
        # Wait between requests to avoid rate limiting
        if not file_exists(translated_audio):
            log_info('Narrator', "Waiting 1 minute before converting Persian script...")
            time.sleep(60)
        
        # Check if translated audio already exists
        if file_exists(translated_audio):
            log_info('Narrator', f"Using existing translation audio: {translated_audio}")
            translated_result = translated_audio
        else:
            log_info('Narrator', "Converting Translation Script to Speech")
            # Initialize TTS client if not already initialized
            if 'client' not in locals():
                client = create_gemini_tts_client(
                    api_key=GEMINI_API_KEY,
                    model=GEMINI_TTS_MODEL,
                    voice=GEMINI_TTS_VOICE,
                    prompt_template=prompt_template,
                    timeout=AI_TIMEOUT
                )
            translated_result = narrate_file(translated_script_file, translated_audio, client, TELEGRAM_AUDIO_TITLE_FA, date_str)
            if translated_result:
                log_success('Narrator', f"Translation script audio created: {translated_result}")
            else:
                log_error('Narrator', "Failed to create required translation script audio")
                return None, None
        
        return summary_result, translated_result
        
    except Exception as e:
        log_error('Narrator', f"Error in narrate function", e)
        return None, None

if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(NARRATED_DIR):
        log_info('Narrator', f"Creating directory: {NARRATED_DIR}")
        os.makedirs(NARRATED_DIR, exist_ok=True)
    
    summary_audio, translated_audio = narrate()
    
    if summary_audio and translated_audio:
        log_success('Narrator', "Narration completed successfully")
        log_info('Narrator', f"Summary audio: {summary_audio}")
        log_info('Narrator', f"Translation audio: {translated_audio}")
    else:
        log_error('Narrator', "Narration failed") 