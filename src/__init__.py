"""
Sumbird - A pipeline for fetching tweets from Twitter/X via RSS, summarizing them with AI (via OpenRouter),
and publishing the summary on Telegraph and Telegram.
"""

__version__ = '1.0.0'

from src.fetcher import fetch_and_format
from src.narrator import narrate
from src.newsletter_generator import generate_newsletter
from src.script_writer import write_scripts
from src.summarizer import summarize
from src.telegram_distributer import distribute, HeadlineClient
from src.telegraph_converter import convert_all_summaries
from src.telegraph_publisher import publish
from src.translator import translate
from utils.html_utils import clean_html_for_display, clean_text, strip_html
from utils.logging_utils import handle_request_error, log_error, log_info, log_success, log_warning

# Define package exports - only include functions that should be part of the public API
__all__ = [
    # Main pipeline components
    'fetch_and_format',
    'summarize',
    'translate',
    'write_scripts',
    'narrate',
    'convert_all_summaries',
    'publish',
    'distribute',
    'generate_newsletter',
    'HeadlineClient',
    
    # Utility functions that are used by multiple modules
    'log_error',
    'handle_request_error',
    'log_info',
    'log_success',
    'log_warning',
    'strip_html',
    'clean_html_for_display',
    'clean_text',
] 