#!/usr/bin/env python3
"""
Module for translating summarized content to Persian.
This module can be run independently or as part of the pipeline.
"""
import os
import httpx
import asyncio
from config import (
    OPENROUTER_API_KEY, TRANSLATOR_PROMPT_PATH, TRANSLATOR_MODEL,
    OPENROUTER_MAX_TOKENS, OPENROUTER_TEMPERATURE, OPENROUTER_SITE_URL,
    OPENROUTER_SITE_NAME, SUMMARY_DIR, TRANSLATED_DIR,
    FILE_FORMAT, get_date_str, get_file_path, AI_TIMEOUT, RETRY_MAX_ATTEMPTS
)
from utils.logging_utils import log_error, handle_request_error
from utils.retry_utils import with_retry_async

class TranslatorClient:
    """Client for interacting with the OpenRouter API for translation."""
    
    def __init__(self, api_key, model, max_tokens, temperature, site_url, site_name):
        """Initialize the OpenRouter client for translation.
        
        Args:
            api_key (str): The OpenRouter API key
            model (str): The model to use for translation
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
    async def translate_text(self, system_prompt, content):
        """Translate content using OpenRouter API with retry logic.
        
        Args:
            system_prompt (str): The system prompt to use
            content (str): The content to translate
            
        Returns:
            tuple: (translated_content, input_tokens, output_tokens)
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
            translation = response_json["choices"][0]["message"]["content"]
            
            # Extract token counts
            usage = response_json.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            return translation, input_tokens, output_tokens

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
            print(f"Summary file not found: {summary_file}")
            return None, 0, 0
            
        with open(summary_file, 'r') as f:
            content_to_translate = f.read()
        
        # Initialize translator client
        client = TranslatorClient(
            api_key=OPENROUTER_API_KEY,
            model=TRANSLATOR_MODEL,
            max_tokens=OPENROUTER_MAX_TOKENS,
            temperature=OPENROUTER_TEMPERATURE,
            site_url=OPENROUTER_SITE_URL,
            site_name=OPENROUTER_SITE_NAME
        )
        
        # Generate translation using async function with asyncio.run
        translation, input_tokens, output_tokens = asyncio.run(client.translate_text(system_prompt, content_to_translate))
        if not translation:
            return None, 0, 0
            
        # Save translation
        translated_file = get_file_path('translated', date_str)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(translated_file), exist_ok=True)
        
        with open(translated_file, 'w') as f:
            f.write(translation)
            
        return translated_file, input_tokens, output_tokens
        
    except Exception as e:
        log_error("Translator", f"Error in translate", e)
        return None, 0, 0

if __name__ == "__main__":
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(SUMMARY_DIR):
        print(f"Creating directory: {SUMMARY_DIR}")
        os.makedirs(SUMMARY_DIR, exist_ok=True)
    
    if not os.path.exists(TRANSLATED_DIR):
        print(f"Creating directory: {TRANSLATED_DIR}")
        os.makedirs(TRANSLATED_DIR, exist_ok=True)
    
    translated_file, input_tokens, output_tokens = translate()
    if translated_file:
        print(f"Translator completed. Output file: {translated_file}")
        print(f"Tokens used: {input_tokens} input, {output_tokens} output")
    else:
        print("Translator failed.") 