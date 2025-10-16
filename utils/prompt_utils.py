#!/usr/bin/env python3
"""
Prompt utilities for Sumbird.

This module provides prompt file loading functionality:
- Loading prompt files with UTF-8 encoding
- Optional default fallback for missing files
- Consistent error handling and logging
"""
import os

from utils.logging_utils import log_error, log_info


def load_prompt(prompt_path: str, default: str = None, strip: bool = True) -> str:
    """Load prompt from file with optional default fallback.
    
    Args:
        prompt_path (str): Path to the prompt file
        default (str, optional): Default prompt to use if file loading fails
        strip (bool): Whether to strip whitespace from the prompt (default: True)
        
    Returns:
        str: Loaded prompt string or default if failed
    """
    try:
        if not os.path.exists(prompt_path):
            if default is not None:
                log_info('PromptUtils', f"Prompt file not found: {prompt_path}, using default")
                return default.strip() if strip else default
            else:
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
            
        if strip:
            prompt = prompt.strip()
            
        return prompt
        
    except FileNotFoundError as e:
        if default is not None:
            log_info('PromptUtils', f"Using default prompt due to file not found: {e}")
            return default.strip() if strip else default
        else:
            log_error('PromptUtils', f"Prompt file not found and no default provided: {e}")
            raise
    except Exception as e:
        if default is not None:
            log_error('PromptUtils', f"Error loading prompt from {prompt_path}: {e}, using default")
            return default.strip() if strip else default
        else:
            log_error('PromptUtils', f"Error loading prompt from {prompt_path}: {e}")
            raise
