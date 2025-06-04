#!/usr/bin/env python3
"""
Environment utilities for Sumbird.

This module provides environment variable management:
- Loading environment variables
- Validating required variables
- Parsing Twitter handles
"""
import os
import sys
from dotenv import load_dotenv
from utils.date_utils import set_timezone
from utils.file_utils import set_file_paths

# Required environment variables
REQUIRED_VARS = [
    'BASE_URL',
    'TARGET_DATE',
    'TIMEZONE',
    'EXPORT_DIR',
    'SUMMARY_DIR',
    'TRANSLATED_DIR',
    'CONVERTED_DIR',
    'PUBLISHED_DIR',
    'NARRATED_DIR',
    'FILE_FORMAT',
    'EXPORT_TITLE_FORMAT',
    'SUMMARY_TITLE_FORMAT',
    'OPENROUTER_API_KEY',
    'SYSTEM_PROMPT_PATH',
    'OPENROUTER_MODEL',
    'OPENROUTER_MAX_TOKENS',
    'OPENROUTER_TEMPERATURE',
    'OPENROUTER_SITE_URL',
    'OPENROUTER_SITE_NAME',
    'TRANSLATOR_MODEL',
    'TRANSLATOR_PROMPT_PATH',
    'SCRIPT_WRITER_MODEL',
    'SCRIPT_WRITER_PROMPT_PATH',
    'SCRIPT_DIR',
    'HEADLINE_WRITER_MODEL',
    'HEADLINE_WRITER_PROMPT_PATH',
    'GEMINI_API_KEY',
    'GEMINI_TTS_MODEL',
    'GEMINI_TTS_VOICE',
    'NARRATOR_PROMPT_PATH',
    'TELEGRAPH_ACCESS_TOKEN',
    'FOOTER_TEXT',
    'FOOTER_LINK_TEXT',
    'FOOTER_LINK_URL',
    'FOOTER_TEXT_FA',
    'FOOTER_LINK_TEXT_FA',
    'FOOTER_LINK_URL_FA',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHAT_ID',
    'TELEGRAM_MESSAGE_TITLE_FORMAT',
    'TELEGRAM_CHANNEL_DISPLAY',
    'TELEGRAM_PARSE_MODE',
    'TELEGRAM_DISABLE_WEB_PREVIEW',
    'TELEGRAM_AUDIO_TITLE_EN',
    'TELEGRAM_AUDIO_TITLE_FA',
    'AUDIO_ARTIST',
    'AUDIO_ALBUM',
    'AUDIO_GENRE'
]

# Storage for loaded environment variables
env_vars = {}

def load_environment():
    """Load environment variables from .env file."""
    # Load environment variables
    load_dotenv()
    
    # Validate required variables
    validate_config()
    
    # Store variables in the env_vars dictionary
    for var in REQUIRED_VARS:
        value = os.getenv(var)
        # Strip inline comments from environment variables
        if value and '#' in value:
            value = value.split('#')[0].strip()
        env_vars[var] = value
    
    # Convert types for numeric values
    env_vars['OPENROUTER_MAX_TOKENS'] = int(env_vars['OPENROUTER_MAX_TOKENS'])
    env_vars['OPENROUTER_TEMPERATURE'] = float(env_vars['OPENROUTER_TEMPERATURE'])
    env_vars['TELEGRAM_DISABLE_WEB_PREVIEW'] = env_vars['TELEGRAM_DISABLE_WEB_PREVIEW'].lower() == 'true'
    
    # Clean up BASE_URL (ensure it ends with a slash)
    env_vars['BASE_URL'] = env_vars['BASE_URL'].rstrip('/') + '/'
    
    # Set timezone in date_utils
    set_timezone(env_vars['TIMEZONE'])
    
    # Set file paths in file_utils
    set_file_paths(
        env_vars['EXPORT_DIR'],
        env_vars['SUMMARY_DIR'],
        env_vars['TRANSLATED_DIR'],
        env_vars['SCRIPT_DIR'],
        env_vars['CONVERTED_DIR'],
        env_vars['PUBLISHED_DIR'],
        env_vars['NARRATED_DIR'],
        env_vars['FILE_FORMAT']
    )
    
    # Parse Twitter handles
    env_vars['HANDLES'] = get_handles_from_env()
    
    return env_vars

def validate_config():
    """Validate that all required environment variables are set."""
    missing_vars = [var for var in REQUIRED_VARS if os.getenv(var) is None]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file based on .env.example")
        sys.exit(1)

def get_handles_from_env():
    """Parse Twitter handles from .env file."""
    handles = []
    try:
        if os.path.exists('.env'):
            with open('.env', 'r') as env_file:
                in_handles_section = False
                for line in env_file:
                    line = line.strip()
                    
                    if line.startswith('HANDLES='):
                        in_handles_section = True
                        first_handle = line[8:].strip()
                        if first_handle:
                            handles.append(first_handle)
                        continue
                    
                    if in_handles_section and line and not line.startswith('#'):
                        if '=' in line:
                            in_handles_section = False
                            continue
                        
                        handles.append(line)
    except Exception as e:
        print(f"Error reading handles from .env: {e}")
    
    if not handles:
        print("Error: No Twitter handles found in .env file")
        print("Please add handles to your .env file after the HANDLES= line")
        sys.exit(1)
    
    return handles

def get_env(var_name, default=None):
    """Get an environment variable value.
    
    Args:
        var_name (str): Name of the environment variable
        default: Default value if not found
        
    Returns:
        The environment variable value or default
    """
    return env_vars.get(var_name, default)

# Initialize environment variables on module import
load_environment() 