# Sumbird

A pipeline for fetching tweets from Twitter/X via RSS, summarizing them with AI, translating to Persian, converting to speech, and publishing to Telegraph and Telegram.

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment: `cp .env.example .env` and edit as needed
4. Set up prompt files: `cp prompts/*.txt.example prompts/*.txt` and customize as needed

## Configuration

All configuration is managed through environment variables. See `.env.example` for a complete list of settings organized by module:

- **API Keys**: OpenRouter, Gemini, Telegraph, and Telegram bot tokens
- **AI Models**: Model selection and parameters for each pipeline step
- **Content Sources**: Twitter/X handles to monitor via RSS
- **Output Formatting**: Telegraph and Telegram message formatting
- **Pipeline Settings**: Thresholds, timeouts, and retry configuration

## Usage

```bash
# Run complete pipeline
python main.py

# Run pipeline without Telegram distribution
python main.py --skip-telegram

# Run test pipeline
python test/test_main.py

# Run test pipeline without Telegram distribution
python test/test_main.py --skip-telegram

# Run individual modules
python -m src.fetcher
python -m src.summarizer
python -m src.translator
python -m src.script_writer
python -m src.narrator
python -m src.telegraph_converter
python -m src.telegraph_publisher
python -m src.telegram_distributer

# Utility scripts
python scripts/telegraph_post_manager.py
```

## Pipeline Flow

1. **Fetch**: Retrieve tweets via RSS feeds
2. **Summarize**: Generate AI summary using OpenRouter
3. **Translate**: Convert to Persian using Gemini
4. **Script**: Optimize content for text-to-speech
5. **Narrate**: Generate audio files using Gemini TTS
6. **Convert**: Format content for Telegraph
7. **Publish**: Create Telegraph posts
8. **Distribute**: Share to Telegram with audio files

## Directory Structure

```
sumbird/
├── src/                    # Core pipeline modules
├── utils/                 # Utility functions
├── data/                  # Pipeline outputs (auto-created)
├── test/                  # Test pipeline and configuration
├── logs/                  # Execution logs (auto-created)
├── prompts/              # AI system prompts
├── scripts/              # Utility scripts
├── main.py               # Pipeline entry point
├── config.py             # Configuration management
└── requirements.txt      # Python dependencies
```

## License

MIT