# Sumbird

A pipeline for fetching tweets from Twitter/X via RSS, summarizing them with AI (via OpenRouter), translating to Persian, and publishing to Telegraph and Telegram.

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment: `cp .env.example .env` and edit as needed
4. Set up prompt files: `cp prompts/*.txt.example prompts/*.txt` and customize as needed

## Key Environment Variables

- `TARGET_DATE`: Date to fetch tweets (YYYY-MM-DD, empty for yesterday)
- `HANDLES`: Twitter/X handles to fetch
- `OPENROUTER_API_KEY`: OpenRouter API key
- `OPENROUTER_MODEL`: AI model to use for summarization (e.g., anthropic/claude-3.7-sonnet, openai/gpt-4o)
- `TRANSLATOR_MODEL`: AI model to use for translation (e.g., google/gemini-2.0-flash-001)
- `OPENROUTER_SITE_URL`: Your site URL for OpenRouter rankings
- `OPENROUTER_SITE_NAME`: Your site name for OpenRouter rankings
- `TELEGRAPH_ACCESS_TOKEN`: Telegraph API token
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Telegram channel ID

## Usage

### Complete Pipeline
```
python main.py
```

### Individual Modules
```
python -m src.fetcher
python -m src.summarizer
python -m src.translator
python -m src.telegraph_converter
python -m src.telegraph_publisher
python -m src.telegram_distributer
```

### Utility Scripts
```
python scripts/telegraph_post_manager.py  # List and delete Telegraph posts
```

## Pipeline Flow

1. `fetcher.py`: Retrieves tweets via RSS feeds
2. `summarizer.py`: Processes tweets with AI (via OpenRouter) to generate a summary
3. `translator.py`: Translates the summary to Persian
4. `telegraph_converter.py`: Formats summaries for Telegraph in both languages
5. `telegraph_publisher.py`: Publishes content to Telegraph
6. `telegram_distributer.py`: Shares to Telegram with links to both versions

## Directory Structure

- `/src`: Core pipeline modules 
- `/utils`: Utility modules used across the pipeline
  - `date_utils.py`: Date and timezone handling
  - `file_utils.py`: File operations and path management
  - `logging_utils.py`: Error logging utilities
  - `html_utils.py`: HTML processing and cleaning
  - `env_utils.py`: Environment variable management
- `/data`: Pipeline outputs
  - `/export`: Raw exported tweets
  - `/summary`: AI-generated summaries
  - `/translated`: Persian translations
  - `/converted`: Telegraph-formatted content
  - `/published`: Published content information
- `/logs`: Execution logs (log.txt, error.log)
- `/prompts`: AI system prompts (Only examples are versioned, copy `.txt.example` to `.txt` to use)

## License

MIT