"""
Utilities package for Sumbird.

This package contains utility modules used across the Sumbird pipeline:
- date_utils: Date and timezone handling
- file_utils: File operations and path management
- logging_utils: Error logging utilities
- html_utils: HTML processing and cleaning
- env_utils: Environment variable management
- retry_utils: Retry mechanisms for network operations
"""

# Date utilities
from utils.date_utils import (
    get_target_date, get_date_str, get_now, 
    format_datetime, format_log_datetime, 
    format_iso_datetime, format_feed_datetime,
    get_date_range, convert_to_timezone,
    DATE_FORMAT, DATETIME_FORMAT, DATETIME_TZ_FORMAT,
    TIME_FORMAT, LOG_DATETIME_FORMAT, FEED_DATETIME_FORMAT
)

# File utilities
from utils.file_utils import (
    get_file_path, ensure_directories,
    file_exists, read_file, write_file
)

# Logging utilities
from utils.logging_utils import (
    log_error, handle_request_error, log_step,
    log_info, log_success, log_warning, log_pipeline_step
)

# HTML utilities
from utils.html_utils import (
    strip_html, clean_html_for_display,
    clean_text, html_to_text
)

# Environment utilities
from utils.env_utils import (
    get_env, load_environment
)

def ensure_environment_loaded():
    """Ensure environment variables are loaded. Safe to call multiple times."""
    from utils import env_utils
    if not env_utils.env_vars:
        env_utils.load_environment()

# Retry utilities
from utils.retry_utils import (
    retry_sync, retry_async, with_retry_sync, with_retry_async
)

# OpenRouter utilities
from utils.openrouter_utils import (
    OpenRouterClient, create_openrouter_client
)

# Gemini utilities
from utils.gemini_utils import (
    GeminiTextClient, create_gemini_text_client,
    GeminiTTSClient, create_gemini_tts_client
) 