# Sumbird

A pipeline for fetching tweets from Twitter/X via RSS, summarizing them with AI (via OpenRouter), translating to Persian, converting to TTS-optimized scripts, converting to speech with TTS, and publishing to Telegraph and Telegram.

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment: `cp .env.example .env` and edit as needed
4. Set up prompt files: `cp prompts/*.txt.example prompts/*.txt` and customize as needed

## Configuration

All configuration is managed through environment variables. See `.env.example` for a complete list of settings organized by module:

- **General Configuration**: Pipeline thresholds, date/timezone settings
- **Fetcher Module**: RSS service URL, Twitter/X handles to monitor
- **Summarizer Module**: OpenRouter API settings for AI summarization
- **Translator Module**: Translation model configuration
- **Script Writer Module**: TTS optimization settings
- **Narrator Module**: Gemini TTS API configuration
- **Telegraph Modules**: Publishing and formatting settings
- **Telegram Module**: Bot configuration and message formatting

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
python -m src.script_writer
python -m src.narrator
python -m src.telegraph_converter
python -m src.telegraph_publisher
python -m src.telegram_distributer
```

### Utility Scripts
```
python scripts/telegraph_post_manager.py  # List and delete Telegraph posts
```

## Pipeline Flow

The pipeline follows a **fail-fast approach** - if any step fails, the entire pipeline stops. All steps are required:

1. **Fetcher**: Retrieves tweets via RSS feeds and formats them
2. **Summarizer**: Processes tweets with AI (via OpenRouter) to generate a summary
3. **Translator**: Translates the summary to Persian
4. **Script Writer**: Converts content to TTS-optimized scripts with natural speech formatting
5. **Narrator**: Converts scripts to speech using Gemini TTS
6. **Telegraph Converter**: Formats summaries for Telegraph in both languages
7. **Telegraph Publisher**: Publishes content to Telegraph
8. **Telegram Distributer**: Shares to Telegram with links and audio files

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
  - `/script`: TTS-optimized scripts
  - `/narrated`: TTS audio files
  - `/converted`: Telegraph-formatted content
  - `/published`: Published content information
- `/logs`: Execution logs (log.txt, error.log)
- `/prompts`: AI system prompts (Only examples are versioned, copy `.txt.example` to `.txt` to use)

## License

MIT