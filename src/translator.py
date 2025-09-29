#!/usr/bin/env python3
"""
Module for translating summarized content to Persian.
This module can be run independently or as part of the pipeline.
"""
import os
from config import (
    GEMINI_API_KEY, TRANSLATOR_PROMPT_PATH, GEMINI_TRANSLATOR_MODEL,
    SUMMARY_DIR, TRANSLATED_DIR, FILE_FORMAT, get_date_str, get_file_path
)
from utils.logging_utils import log_error, log_info, log_success
from utils.gemini_utils import create_gemini_text_client

def translate():
    """Main function to translate summary to Persian using OpenRouter.
    
    Returns:
        tuple: (translated_file_path, input_tokens, output_tokens) or (None, 0, 0) if failed
    """
    try:
        # Get the target date
        date_str = get_date_str()
        
        # Read the translator prompt
        with open(TRANSLATOR_PROMPT_PATH, 'r') as f:
            system_prompt = f.read()
        
        # Read the summarized content
        summary_file = get_file_path('summary', date_str)
        if not os.path.exists(summary_file):
            log_error('Translator', f"Summary file not found: {summary_file}")
            return None, 0, 0
            
        with open(summary_file, 'r') as f:
            content_to_translate = f.read()
        
        # Initialize Gemini translator client
        client = create_gemini_text_client(
            api_key=GEMINI_API_KEY,
            model=GEMINI_TRANSLATOR_MODEL
        )
        
        # Create the full prompt with system prompt and content
        full_prompt = f"{system_prompt}\n\n{content_to_translate}"
        
        # Generate translation using Gemini
        result = client.generate_text(full_prompt)
        if not result:
            return None, 0, 0
        
        # Extract translation and token counts from result
        translation, input_tokens, output_tokens = result
            
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