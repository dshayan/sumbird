#!/usr/bin/env python3
"""
Configuration module for the Sumbird application.
Handles loading and validating environment variables.
"""
from utils import env_utils

# Load environment variables explicitly after imports are complete
env_utils.load_environment()

# Get all environment variables
env_vars = env_utils.env_vars

# General configuration constants
BASE_URL = env_utils.get_env('BASE_URL')

# Nitter service configuration
NITTER_BASE_URL = env_utils.get_env('NITTER_BASE_URL')

# Site URLs
SITE_BASE_URL = env_utils.get_env('SITE_BASE_URL')
OG_IMAGE_URL = env_utils.get_env('OG_IMAGE_URL')

# RSS Feed Configuration
RSS_FEED_TITLE = env_utils.get_env('RSS_FEED_TITLE')
RSS_FEED_DESCRIPTION = env_utils.get_env('RSS_FEED_DESCRIPTION')
RSS_FEED_LANGUAGE = env_utils.get_env('RSS_FEED_LANGUAGE')
RSS_FEED_TTL = int(env_utils.get_env('RSS_FEED_TTL'))
RSS_FEED_GENERATOR = env_utils.get_env('RSS_FEED_GENERATOR')

# Lock file configuration
LOCK_FILE_PATH = env_utils.get_env('LOCK_FILE_PATH')

# Pipeline success thresholds
MIN_FEEDS_TOTAL = int(env_utils.get_env('MIN_FEEDS_TOTAL'))
MIN_FEEDS_SUCCESS_RATIO = float(env_utils.get_env('MIN_FEEDS_SUCCESS_RATIO'))

# Date and timezone configuration
TIMEZONE = env_utils.get_env('TIMEZONE')
TARGET_DATE = env_utils.get_env('TARGET_DATE')

# Directory configuration
EXPORT_DIR = env_utils.get_env('EXPORT_DIR')
SUMMARY_DIR = env_utils.get_env('SUMMARY_DIR')
TRANSLATED_DIR = env_utils.get_env('TRANSLATED_DIR')
SCRIPT_DIR = env_utils.get_env('SCRIPT_DIR')
CONVERTED_DIR = env_utils.get_env('CONVERTED_DIR')
PUBLISHED_DIR = env_utils.get_env('PUBLISHED_DIR')
NARRATED_DIR = env_utils.get_env('NARRATED_DIR')

# Format configuration
FILE_FORMAT = env_utils.get_env('FILE_FORMAT')
EXPORT_TITLE_FORMAT = env_utils.get_env('EXPORT_TITLE_FORMAT')
SUMMARY_TITLE_FORMAT = env_utils.get_env('SUMMARY_TITLE_FORMAT')

# AI Configuration
OPENROUTER_API_KEY = env_utils.get_env('OPENROUTER_API_KEY')
SYSTEM_PROMPT_PATH = env_utils.get_env('SYSTEM_PROMPT_PATH')
OPENROUTER_SUMMARIZER_MODEL = env_utils.get_env('OPENROUTER_SUMMARIZER_MODEL')
OPENROUTER_TRANSLATOR_MODEL = env_utils.get_env('OPENROUTER_TRANSLATOR_MODEL')
OPENROUTER_HEADLINE_MODEL = env_utils.get_env('OPENROUTER_HEADLINE_MODEL')
OPENROUTER_MAX_TOKENS = env_utils.get_env('OPENROUTER_MAX_TOKENS')
OPENROUTER_TEMPERATURE = env_utils.get_env('OPENROUTER_TEMPERATURE')
OPENROUTER_SITE_URL = env_utils.get_env('OPENROUTER_SITE_URL')
OPENROUTER_SITE_NAME = env_utils.get_env('OPENROUTER_SITE_NAME')

# Translator Configuration
GEMINI_TRANSLATOR_MODEL = env_utils.get_env('GEMINI_TRANSLATOR_MODEL')
TRANSLATOR_PROMPT_PATH = env_utils.get_env('TRANSLATOR_PROMPT_PATH')

# Script Writer Configuration (using Gemini)
GEMINI_SCRIPT_WRITER_MODEL = env_utils.get_env('GEMINI_SCRIPT_WRITER_MODEL')
SCRIPT_WRITER_PROMPT_PATH = env_utils.get_env('SCRIPT_WRITER_PROMPT_PATH')

# Telegram Headline Writer Configuration (using OpenRouter)
OPENROUTER_HEADLINE_MODEL = env_utils.get_env('OPENROUTER_HEADLINE_MODEL')
HEADLINE_WRITER_PROMPT_PATH = env_utils.get_env('HEADLINE_WRITER_PROMPT_PATH')

# TTS Configuration
GEMINI_API_KEY = env_utils.get_env('GEMINI_API_KEY')
GEMINI_TTS_MODEL = env_utils.get_env('GEMINI_TTS_MODEL')
GEMINI_TTS_VOICE = env_utils.get_env('GEMINI_TTS_VOICE')
NARRATOR_PROMPT_PATH = env_utils.get_env('NARRATOR_PROMPT_PATH')

# Audio metadata configuration
AUDIO_ARTIST = env_utils.get_env('AUDIO_ARTIST')
AUDIO_ALBUM = env_utils.get_env('AUDIO_ALBUM')
AUDIO_GENRE = env_utils.get_env('AUDIO_GENRE')

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
TELEGRAM_CHANNEL_DISPLAY = env_utils.get_env('TELEGRAM_CHANNEL_DISPLAY')
TELEGRAM_PARSE_MODE = env_utils.get_env('TELEGRAM_PARSE_MODE')
TELEGRAM_DISABLE_WEB_PREVIEW = env_utils.get_env('TELEGRAM_DISABLE_WEB_PREVIEW')
TELEGRAM_AUDIO_TITLE_EN = env_utils.get_env('TELEGRAM_AUDIO_TITLE_EN')
TELEGRAM_AUDIO_TITLE_FA = env_utils.get_env('TELEGRAM_AUDIO_TITLE_FA')

# Timeout configuration
RSS_TIMEOUT = int(env_utils.get_env('RSS_TIMEOUT'))
OPENROUTER_TIMEOUT = int(env_utils.get_env('OPENROUTER_TIMEOUT'))
GEMINI_TEXT_TIMEOUT = int(env_utils.get_env('GEMINI_TEXT_TIMEOUT'))
TTS_TIMEOUT = int(env_utils.get_env('TTS_TIMEOUT'))
TELEGRAPH_TIMEOUT = int(env_utils.get_env('TELEGRAPH_TIMEOUT'))
TELEGRAM_MESSAGE_TIMEOUT = int(env_utils.get_env('TELEGRAM_MESSAGE_TIMEOUT'))
TELEGRAM_FILE_TIMEOUT = int(env_utils.get_env('TELEGRAM_FILE_TIMEOUT'))
NETWORK_TIMEOUT = int(env_utils.get_env('NETWORK_TIMEOUT'))

# Retry configuration
RETRY_MAX_ATTEMPTS = int(env_utils.get_env('RETRY_MAX_ATTEMPTS'))

# Fetcher configuration
FETCHER_BATCH_SIZE = int(env_utils.get_env('FETCHER_BATCH_SIZE'))
FETCHER_BATCH_DELAY = float(env_utils.get_env('FETCHER_BATCH_DELAY'))
FETCHER_SESSION_MODE = env_utils.get_env('FETCHER_SESSION_MODE')
FETCHER_REQUEST_DELAY = float(env_utils.get_env('FETCHER_REQUEST_DELAY'))

# Twitter handles to fetch posts from
HANDLES = env_utils.get_env('HANDLES')

# Date utils functions - import from utils
from utils.date_utils import (
    get_target_date, get_date_str, get_now, 
    format_datetime, format_log_datetime, 
    format_iso_datetime, format_feed_datetime,
    get_date_range
)

# File utils functions - import from utils
from utils.file_utils import get_file_path 