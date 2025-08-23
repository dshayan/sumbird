# Sumbird

A comprehensive AI-powered pipeline for fetching tweets from Twitter/X via RSS, summarizing them with AI, translating to Persian, converting to speech, publishing to Telegraph and Telegram, and generating a newsletter website.

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

### Complete Pipeline
```bash
# Run complete pipeline
python main.py

# Run pipeline without Telegram distribution
python main.py --skip-telegram
```

### Test Pipeline
```bash
# Run test pipeline with test configuration
python test/test_main.py

# Run test pipeline without Telegram distribution
python test/test_main.py --skip-telegram
```

### Individual Modules
```bash
# Core pipeline modules (run independently)
python -m src.fetcher                # Fetch tweets from RSS feeds
python -m src.summarizer             # Generate AI summaries
python -m src.translator             # Translate to Persian
python -m src.script_writer          # Optimize for text-to-speech
python -m src.narrator               # Generate audio files
python -m src.telegraph_converter    # Convert for Telegraph
python -m src.telegraph_publisher    # Publish to Telegraph
python -m src.telegram_distributer   # Distribute to Telegram
```

### Utility Scripts
```bash
# Generate newsletter website manually
python scripts/generate_newsletter.py

# Generate without auto-commit
python scripts/generate_newsletter.py --no-commit

# Manage Telegraph posts (list/delete)
python scripts/telegraph_post_manager.py

# Monitor HTTP traffic for fetcher debugging
python scripts/fetcher_monitor.py
```

## Pipeline Flow

1. **Fetch** (`src/fetcher.py`): Retrieve tweets via RSS feeds and format into markdown
2. **Summarize** (`src/summarizer.py`): Generate AI summary using OpenRouter/Claude
3. **Translate** (`src/translator.py`): Convert to Persian using Gemini
4. **Script** (`src/script_writer.py`): Optimize content for text-to-speech
5. **Narrate** (`src/narrator.py`): Generate audio files using Gemini TTS
6. **Convert** (`src/telegraph_converter.py`): Format content for Telegraph
7. **Publish** (`src/telegraph_publisher.py`): Create Telegraph posts
8. **Distribute** (`src/telegram_distributer.py`): Share to Telegram with audio files
9. **Newsletter** (`src/newsletter_generator.py`): Generate website and publish to GitHub Pages

### Manual Newsletter Generation

To generate the newsletter manually:

```bash
# Generate newsletter without committing
python scripts/generate_newsletter.py --no-commit

# Generate and auto-commit to trigger GitHub Pages deployment
python scripts/generate_newsletter.py
```

### Local Development

To preview the newsletter locally:

```bash
# Serve the docs directory locally
cd docs
python -m http.server 8000

# Visit http://localhost:8000
```

## Directory Structure

```
sumbird/
├── src/                           # Core pipeline modules
│   ├── fetcher.py                # RSS feed fetching and markdown formatting
│   ├── summarizer.py             # AI summarization using OpenRouter
│   ├── translator.py             # Persian translation using Gemini
│   ├── script_writer.py          # TTS script optimization
│   ├── narrator.py               # Audio generation using Gemini TTS
│   ├── telegraph_converter.py    # Telegraph content formatting
│   ├── telegraph_publisher.py    # Telegraph publishing
│   ├── telegram_distributer.py   # Telegram distribution with headline generation
│   └── newsletter_generator.py   # Newsletter website generation
├── utils/                         # Utility functions
│   ├── date_utils.py             # Date and timezone handling
│   ├── file_utils.py             # File operations and path management
│   ├── logging_utils.py          # Error logging and API error handling
│   ├── html_utils.py             # HTML processing and text cleaning
│   ├── env_utils.py              # Environment variable management
│   ├── retry_utils.py            # Network retry mechanisms
│   ├── template_utils.py         # Template and component management
│   ├── openrouter_utils.py       # OpenRouter API client
│   ├── gemini_utils.py           # Gemini API clients (text and TTS)
│   └── pipeline_core.py          # Shared pipeline execution logic
├── docs/                          # Newsletter website (GitHub Pages)
│   ├── assets/                   # Website assets
│   │   ├── css/main.css          # Custom CSS with CSS variables
│   │   └── components/           # Reusable HTML components
│   │       ├── header.html       # Site header component
│   │       └── footer.html       # Site footer component
│   ├── posts/                    # Individual newsletter posts
│   │   └── template.html         # Post template
│   ├── page-template.html        # Main page template
│   ├── index.html                # Homepage (auto-generated)
│   ├── page*.html                # Pagination pages (auto-generated)
│   └── feed.xml                  # RSS feed (auto-generated)
├── scripts/                       # Utility scripts
│   ├── generate_newsletter.py    # Standalone newsletter generator
│   ├── telegraph_post_manager.py # Telegraph post management tool
│   └── fetcher_monitor.py        # HTTP traffic monitoring for debugging
├── test/                          # Test pipeline and configuration
├── data/                          # Pipeline outputs (auto-created)
│   ├── export/                   # Raw exported tweets
│   ├── summary/                  # AI-generated summaries
│   ├── translated/               # Persian translations
│   ├── script/                   # TTS-optimized scripts
│   ├── converted/                # Telegraph-formatted content
│   ├── published/                # Published content information
│   └── narrated/                 # Generated audio files
├── logs/                          # Execution logs (auto-created)
├── prompts/                       # AI system prompts
├── main.py                        # Pipeline entry point
├── config.py                      # Configuration management
└── requirements.txt               # Python dependencies
```