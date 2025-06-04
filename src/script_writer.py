#!/usr/bin/env python3
"""
Module for converting summary and translation content to TTS-optimized scripts.
This module can be run independently or as part of the pipeline.
"""
import os
import httpx
import asyncio
from config import (
    OPENROUTER_API_KEY, SCRIPT_WRITER_PROMPT_PATH, SCRIPT_WRITER_MODEL,
    OPENROUTER_MAX_TOKENS, OPENROUTER_TEMPERATURE, OPENROUTER_SITE_URL,
    OPENROUTER_SITE_NAME, SUMMARY_DIR, TRANSLATED_DIR, SCRIPT_DIR,
    FILE_FORMAT, get_date_str, get_file_path, AI_TIMEOUT, RETRY_MAX_ATTEMPTS
)
from utils.logging_utils import log_error, log_info, log_success
from utils.file_utils import file_exists, read_file
from utils.retry_utils import with_retry_async

class ScriptWriterClient:
    """Client for interacting with the OpenRouter API for script writing."""
    
    def __init__(self, api_key, model, max_tokens, temperature, site_url, site_name):
        """Initialize the OpenRouter client for script writing.
        
        Args:
            api_key (str): The OpenRouter API key
            model (str): The model to use for script writing
            max_tokens (int): Maximum tokens for the response
            temperature (float): Temperature for generation
            site_url (str): Site URL for rankings
            site_name (str): Site name for rankings
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.site_url = site_url
        self.site_name = site_name
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name
        }
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    @with_retry_async(timeout=AI_TIMEOUT, max_attempts=RETRY_MAX_ATTEMPTS)
    async def write_script(self, system_prompt, content):
        """Convert content to TTS-optimized script using OpenRouter API with retry logic.
        
        Args:
            system_prompt (str): The system prompt to use
            content (str): The content to convert to script
            
        Returns:
            tuple: (script_content, input_tokens, output_tokens)
        """
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature
                }
            )
            response.raise_for_status()
            response_json = response.json()
            script = response_json["choices"][0]["message"]["content"]
            
            # Extract token counts
            usage = response_json.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            return script, input_tokens, output_tokens

def write_script_for_file(input_file, output_file, client, system_prompt):
    """Convert a single file to TTS-optimized script.
    
    Args:
        input_file (str): Path to the input file
        output_file (str): Path to save the script file
        client (ScriptWriterClient): Script writer client instance
        system_prompt (str): The system prompt to use
        
    Returns:
        tuple: (output_file_path, input_tokens, output_tokens) or (None, 0, 0) if failed
    """
    try:
        if not file_exists(input_file):
            log_error('ScriptWriter', f"Input file not found: {input_file}")
            return None, 0, 0
        
        # Read the file content
        content = read_file(input_file)
        
        if not content.strip():
            log_error('ScriptWriter', f"No content found in {input_file}")
            return None, 0, 0
        
        log_info('ScriptWriter', f"Processing {input_file}")
        log_info('ScriptWriter', f"Content preview: {content[:200]}...")
        
        # Generate script using async function with asyncio.run
        script, input_tokens, output_tokens = asyncio.run(client.write_script(system_prompt, content))
        if not script:
            return None, 0, 0
            
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save script
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(script)
            
        return output_file, input_tokens, output_tokens
        
    except Exception as e:
        log_error('ScriptWriter', f"Error processing file {input_file}", e)
        return None, 0, 0

def write_scripts():
    """Main function to convert summary and translation files to TTS-optimized scripts.
    
    Returns:
        tuple: (summary_script_path, translated_script_path, total_input_tokens, total_output_tokens) 
               where paths are strings or None if failed
    """
    try:
        # Get the target date
        date_str = get_date_str()
        
        # Read the script writer prompt
        system_prompt = read_file(SCRIPT_WRITER_PROMPT_PATH).strip()
        
        # Get file paths
        summary_file = get_file_path('summary', date_str)
        translated_file = get_file_path('translated', date_str)
        
        # Verify both required files exist
        if not file_exists(summary_file):
            log_error('ScriptWriter', f"Required summary file not found: {summary_file}")
            return None, None, 0, 0
        
        if not file_exists(translated_file):
            log_error('ScriptWriter', f"Required translated file not found: {translated_file}")
            return None, None, 0, 0
        
        # Generate output paths
        summary_script = get_file_path('script', date_str)
        translated_script = get_file_path('script', date_str, lang='FA')
        
        summary_result = None
        translated_result = None
        total_input_tokens = 0
        total_output_tokens = 0
        
        # Check if summary script already exists
        if file_exists(summary_script):
            log_info('ScriptWriter', f"Using existing summary script: {summary_script}")
            summary_result = summary_script
        else:
            log_info('ScriptWriter', "Converting Summary to Script")
            client = ScriptWriterClient(
                api_key=OPENROUTER_API_KEY,
                model=SCRIPT_WRITER_MODEL,
                max_tokens=OPENROUTER_MAX_TOKENS,
                temperature=OPENROUTER_TEMPERATURE,
                site_url=OPENROUTER_SITE_URL,
                site_name=OPENROUTER_SITE_NAME
            )
            summary_result, input_tokens, output_tokens = write_script_for_file(
                summary_file, summary_script, client, system_prompt
            )
            if summary_result:
                log_success('ScriptWriter', f"Scripted using {input_tokens} input tokens, {output_tokens} output tokens")
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
            else:
                log_error('ScriptWriter', "Failed to create required summary script")
                return None, None, 0, 0
        
        # Check if translated script already exists
        if file_exists(translated_script):
            log_info('ScriptWriter', f"Using existing translation script: {translated_script}")
            translated_result = translated_script
        else:
            log_info('ScriptWriter', "Converting Translation to Script")
            # Initialize script writer client if not already initialized
            if 'client' not in locals():
                client = ScriptWriterClient(
                    api_key=OPENROUTER_API_KEY,
                    model=SCRIPT_WRITER_MODEL,
                    max_tokens=OPENROUTER_MAX_TOKENS,
                    temperature=OPENROUTER_TEMPERATURE,
                    site_url=OPENROUTER_SITE_URL,
                    site_name=OPENROUTER_SITE_NAME
                )
            translated_result, input_tokens, output_tokens = write_script_for_file(
                translated_file, translated_script, client, system_prompt
            )
            if translated_result:
                log_success('ScriptWriter', f"Scripted using {input_tokens} input tokens, {output_tokens} output tokens")
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
            else:
                log_error('ScriptWriter', "Failed to create required translation script")
                return None, None, 0, 0
        
        return summary_result, translated_result, total_input_tokens, total_output_tokens
        
    except Exception as e:
        log_error('ScriptWriter', f"Error in write_scripts function", e)
        return None, None, 0, 0

if __name__ == "__main__":
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(SCRIPT_DIR):
        log_info('ScriptWriter', f"Creating directory: {SCRIPT_DIR}")
        os.makedirs(SCRIPT_DIR, exist_ok=True)
    
    summary_script, translated_script, input_tokens, output_tokens = write_scripts()
    
    if summary_script and translated_script:
        log_success('ScriptWriter', "Script writing completed successfully")
        log_info('ScriptWriter', f"Summary script: {summary_script}")
        log_info('ScriptWriter', f"Translation script: {translated_script}")
        log_info('ScriptWriter', f"Total tokens used: {input_tokens} input, {output_tokens} output")
    else:
        log_error('ScriptWriter', "Script writing failed") 