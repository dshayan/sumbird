#!/usr/bin/env python3
"""
Module for processing exported tweets with OpenRouter AI to generate summaries.
This module can be run independently or as part of the pipeline.
"""
import os
import asyncio
from config import (
    OPENROUTER_API_KEY, SYSTEM_PROMPT_PATH, OPENROUTER_MODEL,
    OPENROUTER_MAX_TOKENS, OPENROUTER_TEMPERATURE, OPENROUTER_SITE_URL,
    OPENROUTER_SITE_NAME, SUMMARY_TITLE_FORMAT, EXPORT_DIR, SUMMARY_DIR,
    FILE_FORMAT, get_date_str, get_file_path
)
from utils.logging_utils import log_error, log_info, log_success
from utils.openrouter_utils import create_openrouter_client

def summarize():
    """Main function to summarize exported tweets using OpenRouter.
    
    Returns:
        tuple: (summary_file_path, input_tokens, output_tokens) or (None, 0, 0) if failed
    """
    try:
        # Get the target date
        date_str = get_date_str()
        
        # Read the summarizer prompt
        with open(SYSTEM_PROMPT_PATH, 'r') as f:
            system_prompt = f.read()
        
        # Read the exported content
        export_file = get_file_path('export', date_str)
        if not os.path.exists(export_file):
            log_error('Summarizer', f"Export file not found: {export_file}")
            return None, 0, 0
            
        with open(export_file, 'r') as f:
            user_prompt = f.read()
        
        # Initialize OpenRouter client
        client = create_openrouter_client(
            api_key=OPENROUTER_API_KEY,
            model=OPENROUTER_MODEL,
            max_tokens=OPENROUTER_MAX_TOKENS,
            temperature=OPENROUTER_TEMPERATURE,
            site_url=OPENROUTER_SITE_URL,
            site_name=OPENROUTER_SITE_NAME
        )
        
        # Generate summary using async function with asyncio.run
        summary, input_tokens, output_tokens = asyncio.run(client.generate_completion(system_prompt, user_prompt))
        if not summary:
            return None, 0, 0
            
        # Format and save summary
        formatted_summary = f"<h1>{SUMMARY_TITLE_FORMAT.format(date=date_str)}</h1>\n\n{summary}"
        summary_file = get_file_path('summary', date_str)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(summary_file), exist_ok=True)
        
        with open(summary_file, 'w') as f:
            f.write(formatted_summary)
            
        return summary_file, input_tokens, output_tokens
        
    except Exception as e:
        log_error("Summarizer", f"Error in summarize", e)
        return None, 0, 0

if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(EXPORT_DIR):
        log_info('Summarizer', f"Creating directory: {EXPORT_DIR}")
        os.makedirs(EXPORT_DIR, exist_ok=True)
    
    if not os.path.exists(SUMMARY_DIR):
        log_info('Summarizer', f"Creating directory: {SUMMARY_DIR}")
        os.makedirs(SUMMARY_DIR, exist_ok=True)
    
    summary_file, input_tokens, output_tokens = summarize()
    if summary_file:
        log_success('Summarizer', f"Summarizer completed. Output file: {summary_file}")
        log_info('Summarizer', f"Tokens used: {input_tokens} input, {output_tokens} output")
    else:
        log_error('Summarizer', "Summarizer failed.")