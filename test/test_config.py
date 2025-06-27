#!/usr/bin/env python3
"""
Test configuration for Sumbird pipeline.

This module imports the base configuration and overrides specific parameters
for test mode execution, including test Telegram channel and isolated file paths.

Note: Test mode inherits all AI model configurations from main config.py:
- Translation: Uses Gemini (GEMINI_TRANSLATOR_MODEL)
- Script Writing: Uses Gemini (GEMINI_SCRIPT_WRITER_MODEL)
- Summarization: Uses OpenRouter (OPENROUTER_SUMMARIZER_MODEL)
- TTS: Uses Gemini (GEMINI_TTS_MODEL)
- Telegram Headlines: Uses Gemini (GEMINI_TELEGRAM_MODEL)
"""
import os
import sys

# Add parent directory to path to import from main project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all base configuration (includes new Gemini model configs)
from config import *
from utils import env_utils
from utils.date_utils import get_date_str

# Override Telegram configuration for test channel
TEST_TELEGRAM_CHAT_ID = env_utils.get_env('TEST_TELEGRAM_CHAT_ID')

# Override the Telegram configuration for test mode
TELEGRAM_CHAT_ID = TEST_TELEGRAM_CHAT_ID

# Override Telegraph title format to include TEST- prefix for URLs
# This will make Telegraph URLs start with TEST- (e.g., https://telegra.ph/TEST-AI-Updates-on-2025-06-03...)
TEST_SUMMARY_TITLE_FORMAT = env_utils.get_env('TEST_SUMMARY_TITLE_FORMAT')
SUMMARY_TITLE_FORMAT = TEST_SUMMARY_TITLE_FORMAT

# Override directory paths for test mode - use test/data/ structure
EXPORT_DIR = "test/data/export"
SUMMARY_DIR = "test/data/summary"
TRANSLATED_DIR = "test/data/translated"
SCRIPT_DIR = "test/data/script"
CONVERTED_DIR = "test/data/converted"
PUBLISHED_DIR = "test/data/published"
NARRATED_DIR = "test/data/narrated"

# Test mode flag
TEST_MODE = True

def get_test_file_path(file_type, date_str=None, lang=None):
    """Get file path for test mode using test/data/ directories.
    
    Args:
        file_type (str): Type of file
        date_str (str, optional): Date string
        lang (str, optional): Language code
    
    Returns:
        str: Test mode file path
    """
    if date_str is None:
        date_str = get_date_str()
    
    # Map file types to test directories and formats
    type_map = {
        'export': (EXPORT_DIR, FILE_FORMAT.replace('.html', '.md')),  # Export uses markdown
        'summary': (SUMMARY_DIR, FILE_FORMAT),  # Summary uses HTML
        'translated': (TRANSLATED_DIR, FILE_FORMAT),  # Translated uses HTML
        'script': (SCRIPT_DIR, FILE_FORMAT),  # Script uses HTML
        'converted': (CONVERTED_DIR, FILE_FORMAT.replace('.html', '.json')),  # Converted uses JSON
        'published': (PUBLISHED_DIR, FILE_FORMAT.replace('.html', '.json')),  # Published uses JSON
        'narrated': (NARRATED_DIR, FILE_FORMAT.replace('.html', '.mp3'))  # Narrated uses MP3
    }
    
    if file_type not in type_map:
        raise ValueError(f"Unknown file type: {file_type}")
    
    directory, format_str = type_map[file_type]
    
    # Add language suffix if specified
    if lang:
        # For date-based format strings (e.g., "X-{date}.html")
        if "{date}" in format_str:
            # Add language suffix before file extension
            base, ext = os.path.splitext(format_str)
            file_path = os.path.join(directory, f"{base}-{lang}{ext}".format(date=date_str))
        else:
            # For non-date-based format strings, just add language suffix
            base, ext = os.path.splitext(format_str)
            file_path = os.path.join(directory, f"{base}-{lang}{ext}")
    else:
        file_path = os.path.join(directory, format_str.format(date=date_str))
    
    return file_path

# Override the get_file_path function for test mode
get_file_path = get_test_file_path

def ensure_directories():
    """Ensure all test directories exist."""
    test_dirs = [
        EXPORT_DIR,
        SUMMARY_DIR, 
        TRANSLATED_DIR,
        SCRIPT_DIR,
        CONVERTED_DIR,
        PUBLISHED_DIR,
        NARRATED_DIR,
        "logs"  # Logs directory is shared
    ]
    
    import os
    for directory in test_dirs:
        os.makedirs(directory, exist_ok=True) 