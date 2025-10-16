#!/usr/bin/env python3
"""
Module for converting text content to speech using Gemini 2.5 Flash TTS.
This module can be run independently or as part of the pipeline.
"""
import os
import time
from pathlib import Path

from config import (
    AUDIO_ALBUM, AUDIO_ARTIST, AUDIO_GENRE, GEMINI_API_KEY,
    GEMINI_TTS_MODEL, GEMINI_TTS_VOICE, NARRATED_DIR, NARRATOR_PROMPT_PATH,
    SCRIPT_DIR, TELEGRAM_AUDIO_TITLE_EN, TELEGRAM_AUDIO_TITLE_FA,
    TTS_TIMEOUT, get_date_str, get_file_path
)
from utils.file_utils import file_exists, read_file
from utils.gemini_utils import create_gemini_tts_client
from utils.html_utils import html_to_text
from utils.logging_utils import log_error, log_info, log_success
from utils.prompt_utils import load_prompt

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
        tuple: (audio_file_path, input_tokens, output_tokens) or (None, 0, 0) if failed
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
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convert to speech
        return client.text_to_speech(text_content, output_path, title, AUDIO_ARTIST, AUDIO_ALBUM, AUDIO_GENRE, date_str)
        
    except Exception as e:
        log_error('Narrator', f"Error processing file {file_path}", e)
        return None, 0, 0

def narrate(force_override=False):
    """Main function to convert summary and translated files to speech.
    
    Args:
        force_override (bool): Whether to force regeneration of existing files
    
    Returns:
        tuple: (summary_audio_path, translated_audio_path, total_input_tokens, total_output_tokens) 
               where paths are strings or None if failed
    """
    try:
        # Get the target date
        date_str = get_date_str()
        
        # Read the narrator prompt
        prompt_template = load_prompt(NARRATOR_PROMPT_PATH)
        
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
        total_input_tokens = 0
        total_output_tokens = 0
        
        # Check if summary audio already exists
        if file_exists(summary_audio) and not force_override:
            log_info('Narrator', f"Using existing summary audio: {summary_audio}")
            summary_result = summary_audio
        else:
            log_info('Narrator', "Converting Script to Speech")
            client = create_gemini_tts_client(
                api_key=GEMINI_API_KEY,
                model=GEMINI_TTS_MODEL,
                voice=GEMINI_TTS_VOICE,
                prompt_template=prompt_template
            )
            result = narrate_file(script_file, summary_audio, client, TELEGRAM_AUDIO_TITLE_EN, date_str)
            if result[0]:  # Check if audio file path is not None
                summary_result, input_tokens, output_tokens = result
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                log_success('Narrator', f"Script audio created: {summary_result}")
            else:
                log_error('Narrator', "Failed to create required script audio")
                return None, None, 0, 0
        
        # Wait between requests to avoid rate limiting
        if not file_exists(translated_audio) or force_override:
            log_info('Narrator', "Waiting 1 minute before converting Persian script...")
            time.sleep(60)
        
        # Check if translated audio already exists
        if file_exists(translated_audio) and not force_override:
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
                    prompt_template=prompt_template
                )
            result = narrate_file(translated_script_file, translated_audio, client, TELEGRAM_AUDIO_TITLE_FA, date_str)
            if result[0]:  # Check if audio file path is not None
                translated_result, input_tokens, output_tokens = result
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                log_success('Narrator', f"Translation script audio created: {translated_result}")
            else:
                log_error('Narrator', "Failed to create required translation script audio")
                return None, None, 0, 0
        
        # Log completion and token usage
        log_success('Narrator', "Narration completed successfully")
        log_info('Narrator', f"Summary audio: {summary_result}")
        log_info('Narrator', f"Translation audio: {translated_result}")
        log_info('Narrator', f"Tokens used: {total_input_tokens} input, {total_output_tokens} output")
        
        return summary_result, translated_result, total_input_tokens, total_output_tokens
        
    except Exception as e:
        log_error('Narrator', f"Error in narrate function", e)
        return None, None, 0, 0

if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(NARRATED_DIR):
        log_info('Narrator', f"Creating directory: {NARRATED_DIR}")
        os.makedirs(NARRATED_DIR, exist_ok=True)
    
    summary_audio, translated_audio, input_tokens, output_tokens = narrate()
    
    if summary_audio and translated_audio:
        log_success('Narrator', "Narration completed successfully")
        log_info('Narrator', f"Summary audio: {summary_audio}")
        log_info('Narrator', f"Translation audio: {translated_audio}")
        log_info('Narrator', f"Tokens used: {input_tokens} input, {output_tokens} output")
    else:
        log_error('Narrator', "Narration failed") 