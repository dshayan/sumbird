#!/usr/bin/env python3
"""
Module for processing exported tweets with OpenRouter AI to generate summaries.
This module can be run independently or as part of the pipeline.
"""
import os
import httpx
import asyncio
from config import (
    OPENROUTER_API_KEY, SYSTEM_PROMPT_PATH, OPENROUTER_MODEL,
    OPENROUTER_MAX_TOKENS, OPENROUTER_TEMPERATURE, OPENROUTER_SITE_URL,
    OPENROUTER_SITE_NAME, SUMMARY_TITLE_FORMAT, EXPORT_DIR, SUMMARY_DIR,
    FILE_FORMAT, get_date_str, get_file_path, AI_TIMEOUT, RETRY_MAX_ATTEMPTS
)
from utils.logging_utils import log_error, log_info, log_success
from utils.retry_utils import with_retry_async

class OpenRouterClient:
    """Client for interacting with the OpenRouter API."""
    
    def __init__(self, api_key, model, max_tokens, temperature, site_url, site_name):
        """Initialize the OpenRouter client.
        
        Args:
            api_key (str): The OpenRouter API key
            model (str): The model to use
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
    async def generate_summary(self, system_prompt, user_prompt):
        """Generate a summary using OpenRouter API with retry logic.
        
        Args:
            system_prompt (str): The system prompt to use
            user_prompt (str): The user prompt containing tweets to summarize
            
        Returns:
            tuple: (generated_summary, input_tokens, output_tokens)
        """
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            response = await client.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature
                }
            )
            response.raise_for_status()
            response_json = response.json()
            summary = response_json["choices"][0]["message"]["content"]
            
            # Extract token counts
            usage = response_json.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            return summary, input_tokens, output_tokens

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
        client = OpenRouterClient(
            api_key=OPENROUTER_API_KEY,
            model=OPENROUTER_MODEL,
            max_tokens=OPENROUTER_MAX_TOKENS,
            temperature=OPENROUTER_TEMPERATURE,
            site_url=OPENROUTER_SITE_URL,
            site_name=OPENROUTER_SITE_NAME
        )
        
        # Generate summary using async function with asyncio.run
        summary, input_tokens, output_tokens = asyncio.run(client.generate_summary(system_prompt, user_prompt))
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