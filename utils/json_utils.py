#!/usr/bin/env python3
"""
JSON utilities for Sumbird.

This module provides JSON file operations:
- Reading JSON files with UTF-8 encoding
- Writing JSON files with consistent formatting
- Error handling and logging
"""
import json
import os

from utils.logging_utils import log_error, log_info


def read_json(file_path: str) -> dict:
    """Read and parse JSON file with UTF-8 encoding.
    
    Args:
        file_path (str): Path to the JSON file to read
        
    Returns:
        dict: Parsed JSON data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"JSON file not found: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return data
        
    except FileNotFoundError as e:
        log_error('JsonUtils', f"File not found: {e}")
        raise
    except json.JSONDecodeError as e:
        log_error('JsonUtils', f"Invalid JSON in file {file_path}: {e}")
        raise
    except Exception as e:
        log_error('JsonUtils', f"Error reading JSON file {file_path}: {e}")
        raise


def write_json(file_path: str, data: dict, ensure_ascii: bool = False, indent: int = 2) -> bool:
    """Write data to JSON file with UTF-8 encoding and formatting.
    
    Args:
        file_path (str): Path to save the JSON file
        data (dict): Data to write as JSON
        ensure_ascii (bool): Whether to ensure ASCII encoding (default: False for UTF-8)
        indent (int): Number of spaces for indentation (default: 2)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
            
        return True
        
    except Exception as e:
        log_error('JsonUtils', f"Error writing JSON file {file_path}: {e}")
        return False
