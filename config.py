#!/usr/bin/env python3
"""
Configuration module for the Sumbird application.
Handles loading and validating environment variables.
"""
from utils import env_utils

# Get all environment variables
env_vars = env_utils.env_vars

# General configuration constants
BASE_URL = env_utils.get_env('BASE_URL')

# Pipeline success thresholds
MIN_FEEDS_TOTAL = int(env_utils.get_env('MIN_FEEDS_TOTAL', '50'))
MIN_FEEDS_SUCCESS_RATIO = float(env_utils.get_env('MIN_FEEDS_SUCCESS_RATIO', '0.9'))

# Date and timezone configuration
TIMEZONE = env_utils.get_env('TIMEZONE')
TARGET_DATE = env_utils.get_env('TARGET_DATE')

# Directory configuration
EXPORT_DIR = env_utils.get_env('EXPORT_DIR')
SUMMARY_DIR = env_utils.get_env('SUMMARY_DIR')
TRANSLATED_DIR = env_utils.get_env('TRANSLATED_DIR')
CONVERTED_DIR = env_utils.get_env('CONVERTED_DIR')
PUBLISHED_DIR = env_utils.get_env('PUBLISHED_DIR')

# Format configuration
FILE_FORMAT = env_utils.get_env('FILE_FORMAT')
EXPORT_TITLE_FORMAT = env_utils.get_env('EXPORT_TITLE_FORMAT')
SUMMARY_TITLE_FORMAT = env_utils.get_env('SUMMARY_TITLE_FORMAT')

# AI Configuration
OPENROUTER_API_KEY = env_utils.get_env('OPENROUTER_API_KEY')
SYSTEM_PROMPT_PATH = env_utils.get_env('SYSTEM_PROMPT_PATH')
OPENROUTER_MODEL = env_utils.get_env('OPENROUTER_MODEL')
OPENROUTER_MAX_TOKENS = env_utils.get_env('OPENROUTER_MAX_TOKENS')
OPENROUTER_TEMPERATURE = env_utils.get_env('OPENROUTER_TEMPERATURE')
OPENROUTER_SITE_URL = env_utils.get_env('OPENROUTER_SITE_URL')
OPENROUTER_SITE_NAME = env_utils.get_env('OPENROUTER_SITE_NAME')

# Translator Configuration
TRANSLATOR_MODEL = env_utils.get_env('TRANSLATOR_MODEL')
TRANSLATOR_PROMPT_PATH = env_utils.get_env('TRANSLATOR_PROMPT_PATH')

# Telegraph configuration
TELEGRAPH_ACCESS_TOKEN = env_utils.get_env('TELEGRAPH_ACCESS_TOKEN')

# Footer configuration
FOOTER_TEXT = env_utils.get_env('FOOTER_TEXT')
FOOTER_LINK_TEXT = env_utils.get_env('FOOTER_LINK_TEXT')
FOOTER_LINK_URL = env_utils.get_env('FOOTER_LINK_URL')
FOOTER_TEXT_FA = env_utils.get_env('FOOTER_TEXT_FA')
FOOTER_LINK_TEXT_FA = env_utils.get_env('FOOTER_LINK_TEXT_FA')
FOOTER_LINK_URL_FA = env_utils.get_env('FOOTER_LINK_URL_FA')

# Telegram configuration
TELEGRAM_BOT_TOKEN = env_utils.get_env('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = env_utils.get_env('TELEGRAM_CHAT_ID')
TELEGRAM_MESSAGE_TITLE_FORMAT = env_utils.get_env('TELEGRAM_MESSAGE_TITLE_FORMAT')
TELEGRAM_SUMMARY_FORMAT = env_utils.get_env('TELEGRAM_SUMMARY_FORMAT')
TELEGRAM_CHANNEL_DISPLAY = env_utils.get_env('TELEGRAM_CHANNEL_DISPLAY')
TELEGRAM_PARSE_MODE = env_utils.get_env('TELEGRAM_PARSE_MODE')
TELEGRAM_DISABLE_WEB_PREVIEW = env_utils.get_env('TELEGRAM_DISABLE_WEB_PREVIEW')

# Twitter handles to fetch posts from
HANDLES = env_utils.get_env('HANDLES')

# Date utils functions - import from utils
from utils.date_utils import (
    get_target_date, get_date_str, get_now, 
    format_datetime, format_log_datetime, 
    format_iso_datetime, format_feed_datetime
)

# File utils functions - import from utils
from utils.file_utils import get_file_path 