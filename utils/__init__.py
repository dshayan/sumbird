"""
Utilities package for Sumbird.

This package contains utility modules used across the Sumbird pipeline:
- date_utils: Date and timezone handling
- file_utils: File operations and path management
- logging_utils: Error logging utilities
- html_utils: HTML processing and cleaning
- env_utils: Environment variable management
- retry_utils: Retry mechanisms for network operations
- template_utils: Template and component management for external CSS system
"""

from utils.date_utils import (
    DATE_FORMAT, DATETIME_FORMAT, DATETIME_TZ_FORMAT, FEED_DATETIME_FORMAT,
    LOG_DATETIME_FORMAT, TIME_FORMAT, convert_to_timezone, format_datetime,
    format_feed_datetime, format_iso_datetime, format_log_datetime,
    get_date_range, get_date_str, get_now, get_target_date
)
from utils.env_utils import get_env, load_environment
from utils.file_utils import ensure_directories, file_exists, get_file_path, read_file, write_file
from utils.json_utils import read_json, write_json
from utils.prompt_utils import load_prompt
from utils.gemini_utils import (
    GeminiTTSClient, GeminiTextClient, create_gemini_text_client,
    create_gemini_tts_client
)
from utils.html_utils import clean_html_for_display, clean_text, html_to_text, strip_html
from utils.logging_utils import (
    handle_request_error, log_error, log_info,
    log_step, log_success, log_warning
)
from utils.openrouter_utils import OpenRouterClient, create_openrouter_client
from utils.pipeline_core import run_pipeline_core
from utils.retry_utils import retry_async, retry_sync, with_retry_async, with_retry_sync
from utils.template_utils import TemplateManager, create_template_manager


def ensure_environment_loaded():
    """Ensure environment variables are loaded. Safe to call multiple times."""
    from utils import env_utils
    if not env_utils.env_vars:
        env_utils.load_environment() 