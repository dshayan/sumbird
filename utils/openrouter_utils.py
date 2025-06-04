#!/usr/bin/env python3
"""
OpenRouter API utilities for Sumbird pipeline.
Provides a centralized client for interacting with OpenRouter API.
"""
import httpx
from utils.retry_utils import with_retry_async
from utils.logging_utils import log_error


class OpenRouterClient:
    """Client for interacting with the OpenRouter API."""
    
    def __init__(self, api_key, model, max_tokens, temperature, site_url, site_name, timeout=120):
        """Initialize the OpenRouter client.
        
        Args:
            api_key (str): The OpenRouter API key
            model (str): The model to use
            max_tokens (int): Maximum tokens for the response
            temperature (float): Temperature for generation
            site_url (str): Site URL for rankings
            site_name (str): Site name for rankings
            timeout (int): Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.site_url = site_url
        self.site_name = site_name
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name
        }
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    @with_retry_async(timeout=120, max_attempts=3)
    async def generate_completion(self, system_prompt, user_prompt):
        """Generate a completion using OpenRouter API with retry logic.
        
        Args:
            system_prompt (str): The system prompt to use
            user_prompt (str): The user prompt containing content to process
            
        Returns:
            tuple: (generated_content, input_tokens, output_tokens)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
            content = response_json["choices"][0]["message"]["content"]
            
            # Extract token counts
            usage = response_json.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            return content, input_tokens, output_tokens


def create_openrouter_client(api_key, model, max_tokens=4000, temperature=0, site_url="", site_name="", timeout=120):
    """Factory function to create an OpenRouter client with default parameters.
    
    Args:
        api_key (str): The OpenRouter API key
        model (str): The model to use
        max_tokens (int): Maximum tokens for the response
        temperature (float): Temperature for generation
        site_url (str): Site URL for rankings
        site_name (str): Site name for rankings
        timeout (int): Request timeout in seconds
        
    Returns:
        OpenRouterClient: Configured client instance
    """
    return OpenRouterClient(
        api_key=api_key,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        site_url=site_url,
        site_name=site_name,
        timeout=timeout
    ) 