"""
Sumbird - A pipeline for fetching tweets from Twitter/X via RSS, summarizing them with AI (via OpenRouter),
and publishing the summary on Telegraph and Telegram.
"""

# Define the version
__version__ = '1.0.0'

# Import main components for easier access
from src.fetcher import fetch_and_format
from src.summarizer import summarize
from src.translator import translate
from src.script_writer import write_scripts
from src.narrator import narrate
from src.telegraph_converter import convert_all_summaries
from src.telegraph_publisher import publish
from src.telegram_distributer import distribute, HeadlineGenerator

# Import utility functions from the utils package
from utils.logging_utils import log_error, handle_request_error, log_info, log_success, log_warning, log_pipeline_step
from utils.html_utils import strip_html, clean_html_for_display, clean_text

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
    'HeadlineGenerator',
    
    # Utility functions that are used by multiple modules
    'log_error',
    'handle_request_error',
    'log_info',
    'log_success',
    'log_warning',
    'log_pipeline_step',
    'strip_html',
    'clean_html_for_display',
    'clean_text',
] 