#!/usr/bin/env python3
"""
Module for translating summarized content to Persian.
This module can be run independently or as part of the pipeline.
"""
import asyncio
import os

from config import (
    FILE_FORMAT, OPENROUTER_API_KEY, OPENROUTER_MAX_TOKENS,
    OPENROUTER_TRANSLATOR_MODEL, OPENROUTER_SITE_NAME, OPENROUTER_SITE_URL,
    OPENROUTER_TEMPERATURE, SUMMARY_DIR, TRANSLATED_DIR, TRANSLATOR_PROMPT_PATH,
    get_date_str, get_file_path
)
from utils.logging_utils import log_error, log_info, log_success
from utils.openrouter_utils import create_openrouter_client
from utils.prompt_utils import load_prompt

def translate():
    """Main function to translate summary to Persian using OpenRouter.
    
    Returns:
        tuple: (translated_file_path, input_tokens, output_tokens) or (None, 0, 0) if failed
    """
    try:
        # Get the target date
        date_str = get_date_str()
        
        # Read the translator prompt
        system_prompt = load_prompt(TRANSLATOR_PROMPT_PATH)
        
        # Read the summarized content
        summary_file = get_file_path('summary', date_str)
        if not os.path.exists(summary_file):
            log_error('Translator', f"Summary file not found: {summary_file}")
            return None, 0, 0
            
        with open(summary_file, 'r') as f:
            user_prompt = f.read()
        
        # Initialize OpenRouter client
        client = create_openrouter_client(
            api_key=OPENROUTER_API_KEY,
            model=OPENROUTER_TRANSLATOR_MODEL,
            max_tokens=OPENROUTER_MAX_TOKENS,
            temperature=OPENROUTER_TEMPERATURE,
            site_url=OPENROUTER_SITE_URL,
            site_name=OPENROUTER_SITE_NAME
        )
        
        # Generate translation using async function with asyncio.run
        translation, input_tokens, output_tokens = asyncio.run(client.generate_completion(system_prompt, user_prompt))
        if not translation:
            return None, 0, 0
            
        # Save translation
        translated_file = get_file_path('translated', date_str)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(translated_file), exist_ok=True)
        
        with open(translated_file, 'w') as f:
            f.write(translation)
        
        # Log completion and token usage
        log_success('Translator', f"Translator completed. Output file: {translated_file}")
        log_info('Translator', f"Tokens used: {input_tokens} input, {output_tokens} output")
            
        return translated_file, input_tokens, output_tokens
        
    except Exception as e:
        log_error("Translator", f"Error in translate", e)
        return None, 0, 0

if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(SUMMARY_DIR):
        log_info('Translator', f"Creating directory: {SUMMARY_DIR}")
        os.makedirs(SUMMARY_DIR, exist_ok=True)
    
    if not os.path.exists(TRANSLATED_DIR):
        log_info('Translator', f"Creating directory: {TRANSLATED_DIR}")
        os.makedirs(TRANSLATED_DIR, exist_ok=True)
    
    translated_file, input_tokens, output_tokens = translate()
    if translated_file:
        log_success('Translator', f"Translator completed. Output file: {translated_file}")
        log_info('Translator', f"Tokens used: {input_tokens} input, {output_tokens} output")
    else:
        log_error('Translator', "Translator failed.") 