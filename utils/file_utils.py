#!/usr/bin/env python3
"""
File utilities for Sumbird.

This module provides file-related utilities:
- File path generation
- Directory creation
- File operations
"""
import os
from utils.date_utils import get_date_str

# File paths will be set by env_utils during initialization
EXPORT_DIR = None
SUMMARY_DIR = None
TRANSLATED_DIR = None
SCRIPT_DIR = None
CONVERTED_DIR = None
PUBLISHED_DIR = None
NARRATED_DIR = None
FILE_FORMAT = None

def set_file_paths(export_dir, summary_dir, translated_dir, script_dir, converted_dir, published_dir, narrated_dir, file_format):
    """Set the global file path variables."""
    global EXPORT_DIR, SUMMARY_DIR, TRANSLATED_DIR, SCRIPT_DIR, CONVERTED_DIR, PUBLISHED_DIR, NARRATED_DIR, FILE_FORMAT
    EXPORT_DIR = export_dir
    SUMMARY_DIR = summary_dir
    TRANSLATED_DIR = translated_dir
    SCRIPT_DIR = script_dir
    CONVERTED_DIR = converted_dir
    PUBLISHED_DIR = published_dir
    NARRATED_DIR = narrated_dir
    FILE_FORMAT = file_format

def ensure_directories():
    """Ensure all data directories exist."""
    os.makedirs('logs', exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(SUMMARY_DIR, exist_ok=True)
    os.makedirs(TRANSLATED_DIR, exist_ok=True)
    if SCRIPT_DIR:  # Only create if SCRIPT_DIR is configured
        os.makedirs(SCRIPT_DIR, exist_ok=True)
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    os.makedirs(PUBLISHED_DIR, exist_ok=True)
    if NARRATED_DIR:  # Only create if NARRATED_DIR is configured
        os.makedirs(NARRATED_DIR, exist_ok=True)

def get_file_path(file_type, date_str=None, lang=None):
    """Get a file path based on file type and date.
    
    Args:
        file_type (str): Type of file ('export', 'summary', 'translated', 'script', 'converted', 'published', 'narrated')
        date_str (str, optional): Date string. If None, uses the target date.
        lang (str, optional): Language code for language-specific files (e.g., 'FA' for Persian)
    
    Returns:
        str: Full path to the file
        
    Raises:
        ValueError: If the file_type is unknown
    """
    if date_str is None:
        date_str = get_date_str()
    
    # Map file types to directories and formats
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

def get_audio_file_path(file_type, date_str=None, lang=None):
    """Get audio file path, checking for both MP3 and WAV formats.
    
    Args:
        file_type (str): Type of file (should be 'narrated')
        date_str (str, optional): Date string. If None, uses the target date.
        lang (str, optional): Language code for language-specific files (e.g., 'FA' for Persian)
    
    Returns:
        str: Full path to the existing audio file (MP3 preferred, WAV as fallback), or MP3 path if neither exists
    """
    # Get MP3 path (preferred format)
    mp3_path = get_file_path(file_type, date_str, lang)
    
    # Check if MP3 exists
    if file_exists(mp3_path):
        return mp3_path
    
    # If MP3 doesn't exist, check for WAV fallback
    wav_path = mp3_path.replace('.mp3', '.wav')
    if file_exists(wav_path):
        return wav_path
    
    # If neither exists, return the MP3 path (for error messages or file creation)
    return mp3_path

def file_exists(file_path):
    """Check if a file exists.
    
    Args:
        file_path (str): Path to the file
    
    Returns:
        bool: True if the file exists, False otherwise
    """
    return os.path.exists(file_path) and os.path.isfile(file_path)

def read_file(file_path, encoding='utf-8'):
    """Read the contents of a file.
    
    Args:
        file_path (str): Path to the file
        encoding (str): File encoding
    
    Returns:
        str: File contents
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not file_exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()

def write_file(file_path, content, encoding='utf-8'):
    """Write content to a file.
    
    Args:
        file_path (str): Path to the file
        content (str): Content to write
        encoding (str): File encoding
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception:
        return False 