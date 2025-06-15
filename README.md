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
- **Summarizer Module**: OpenRouter API settings for AI summarization with Claude
- **Translator Module**: Translation model configuration for Persian output
- **Script Writer Module**: TTS optimization settings for natural speech
- **Narrator Module**: Gemini TTS API configuration with voice selection
- **Telegraph Modules**: Publishing and formatting settings for both languages
- **Telegram Module**: Bot configuration, message formatting, audio distribution, and headline generation settings

## Usage

### Complete Pipeline
```bash
python main.py
```
Runs the entire pipeline from fetching to distribution.

### Individual Modules
```bash
python -m src.fetcher          # Fetch and format tweets
python -m src.summarizer       # Generate AI summary
python -m src.translator       # Translate to Persian
python -m src.script_writer    # Create TTS-optimized scripts
python -m src.narrator         # Generate speech audio
python -m src.telegraph_converter  # Format for Telegraph
python -m src.telegraph_publisher  # Publish to Telegraph
python -m src.telegram_distributer # Distribute to Telegram (includes headline generation)
```

### Test Pipeline
```bash
python test/test_main.py  # Run complete pipeline in test mode
```

### Utility Scripts
```bash
python scripts/telegraph_post_manager.py  # List and delete Telegraph posts
```

## Pipeline Flow

The pipeline follows a **fail-fast approach** with **robust retry mechanisms** - if any step fails after retries, the entire pipeline stops. All steps are required:

1. **Fetcher**: Retrieves tweets via RSS feeds and formats them
2. **Summarizer**: Processes tweets with AI (via OpenRouter) to generate a summary
3. **Translator**: Translates the summary to Persian
4. **Script Writer**: Converts content to TTS-optimized scripts with natural speech formatting
5. **Narrator**: Converts scripts to speech using Gemini TTS (MP3 preferred, WAV fallback)
6. **Telegraph Converter**: Formats summaries for Telegraph in both languages
7. **Telegraph Publisher**: Publishes content to Telegraph
8. **Telegram Distributer**: Generates engaging headlines and shares to Telegram with links and audio files

## Test Pipeline

The project includes a comprehensive test pipeline that runs the complete workflow in isolation:

- **Isolated Environment**: Uses `test/data/` directories instead of `data/`
- **Test Telegram Channel**: Configurable via `TEST_TELEGRAM_CHAT_ID` environment variable
- **Telegraph Integration**: Publishes to Telegraph with "TEST-" prefix in titles
- **Same AI Models**: Uses identical AI configuration as production pipeline
- **Cached Execution**: Reuses existing test data when available for faster iteration

### Running Tests

```bash
# Run complete test pipeline
python test/test_main.py
```

## Directory Structure

```
sumbird/
├── src/                    # Core pipeline modules
│   ├── fetcher.py         # RSS feed fetching and formatting
│   ├── summarizer.py      # AI summarization with Claude
│   ├── translator.py      # Persian translation
│   ├── script_writer.py   # TTS script optimization
│   ├── narrator.py        # Text-to-speech generation
│   ├── telegraph_converter.py  # Telegraph formatting
│   ├── telegraph_publisher.py  # Telegraph publishing
│   └── telegram_distributer.py # Telegram distribution
├── utils/                 # Utility modules
│   ├── date_utils.py      # Date and timezone handling
│   ├── file_utils.py      # File operations and path management
│   ├── logging_utils.py   # Error logging and retry tracking
│   ├── html_utils.py      # HTML processing and cleaning
│   ├── env_utils.py       # Environment variable management
│   └── retry_utils.py     # Centralized retry mechanisms
├── data/                  # Pipeline outputs (auto-created)
│   ├── export/           # Raw exported tweets
│   ├── summary/          # AI-generated summaries
│   ├── translated/       # Persian translations
│   ├── script/           # TTS-optimized scripts
│   ├── narrated/         # TTS audio files (MP3/WAV)
│   ├── converted/        # Telegraph-formatted content
│   └── published/        # Published content metadata
├── test/                  # Test pipeline
│   ├── test_main.py      # Test pipeline runner
│   ├── test_config.py    # Test configuration overrides
│   └── data/             # Test outputs (auto-created, gitignored)
├── logs/                  # Execution logs (auto-created)
│   ├── log.txt           # Pipeline execution tracking
│   └── error.log         # Detailed error logs with retry information
├── prompts/              # AI system prompts
│   ├── *.txt.example     # Example prompts
│   └── *.txt             # Active prompts (copy from examples)
├── scripts/              # Utility scripts
│   └── telegraph_post_manager.py  # Telegraph post management
├── main.py               # Pipeline entry point
├── config.py             # Configuration management
└── requirements.txt      # Python dependencies
```

## License

MIT