# Sumbird

AI-powered pipeline for automatically fetching Twitter/X content via RSS, processing with AI (summarization, translation, text-to-speech), and publishing to Telegraph, Telegram, and a newsletter website.

**What it does:** Monitors Twitter/X accounts → Summarizes daily posts with AI → Translates to Persian → Generates audio → Publishes everywhere

## Architecture

The pipeline consists of 9 sequential steps:

```
1. Fetch       → Retrieve tweets from Twitter/X handles via Nitter RSS
2. Summarize   → Generate AI summary of daily posts (OpenRouter/Claude)
3. Translate   → Translate summary to Persian (Gemini)
4. Script      → Optimize text for text-to-speech (Gemini)
5. Narrate     → Convert to audio with TTS (Gemini TTS)
6. Convert     → Format content for Telegraph (HTML processing)
7. Publish     → Publish to Telegraph (both EN and FA versions)
8. Distribute  → Send to Telegram channel (messages + audio files)
9. Newsletter  → Generate static website and RSS feed (GitHub Pages)
```

Each step saves its output to the `data/` directory and can be run independently or skipped via command-line flags.

## System Requirements

### Operating System
- **Linux/macOS**: Full support
- **Windows**: Core pipeline works; scheduler script requires WSL/macOS

### Dependencies
- **Python 3.8+**
- **FFmpeg** (required for audio processing)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg` or `sudo yum install ffmpeg`
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org)
- **Docker & Docker Compose** (for Nitter RSS service)

### API Keys Required
- **OpenRouter** (for summarization)
- **Google Gemini** (for translation, script writing, and TTS)
- **Telegraph** (for publishing)
- **Telegram Bot** (for distribution)

## Quick Start

### 1. Install System Dependencies
```bash
# macOS
brew install python3 ffmpeg docker

# Linux (Ubuntu/Debian)
sudo apt update && sudo apt install python3 python3-pip ffmpeg docker.io docker-compose
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy configuration templates
cp .env.example .env
cp prompts/*.txt.example prompts/*.txt

# Edit .env with your API keys and settings
nano .env  # or use your preferred editor
```

**Key settings to configure in `.env`:**
- Add your API keys (OpenRouter, Gemini, Telegraph, Telegram)
- Add Twitter/X handles to monitor (see HANDLES section)
- Set `SITE_BASE_URL` and `OG_IMAGE_URL` for the newsletter site (canonical URLs and social previews)
- Configure timezone (default: UTC)

### 4. Set Up Nitter (RSS Service)
```bash
# Start Nitter service
docker compose up -d

# Create Twitter session tokens (required for RSS access)
# Download the session creation script from Nitter's repository:
# https://github.com/zedeus/nitter/tree/master/tools

pip install requests beautifulsoup4
python3 create_session_browser.py <username> <password> [totp_secret] --append sessions.jsonl

# Restart Nitter to load sessions
docker compose restart nitter

# Verify Nitter is working
curl http://localhost:8080/OpenAI/rss
```

**Note:** Session tokens may expire. If RSS feeds stop working, recreate tokens and restart Nitter.

### 5. Run Pipeline
```bash
# Run complete pipeline
python main.py

# Or run in test mode first (uses separate test directories)
python test/test_main.py --skip-telegram
```

## Configuration Guide

The `.env` file is organized into logical sections:

### API Keys & Authentication
Essential credentials for external services:
- `OPENROUTER_API_KEY`: For AI summarization (Claude Sonnet)
- `GEMINI_API_KEY`: For translation, script writing, and TTS
- `TELEGRAPH_ACCESS_TOKEN`: For publishing articles
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: For distribution

### AI Models & Behavior
Control which AI models to use and how they behave:
- `OPENROUTER_SUMMARIZER_MODEL`: Model for summarization (default: Claude Sonnet 4)
- `GEMINI_TRANSLATOR_MODEL`: Model for translation (default: Gemini Flash)
- `GEMINI_TTS_VOICE`: Voice for audio generation (Zephyr, Aoede, Charon, Fenrir)
- `OPENROUTER_TEMPERATURE`: AI creativity (0 = deterministic, 1 = creative)

### Content Sources
Twitter/X accounts to monitor:
```bash
HANDLES=
OpenAI
AnthropicAI
GoogleDeepMind
```

### Pipeline Thresholds
Quality control settings:
- `MIN_FEEDS_TOTAL`: Minimum feeds required for pipeline to run (default: 50)
- `MIN_FEEDS_SUCCESS_RATIO`: Minimum success rate (default: 0.9 = 90%)

### Timeout & Retry Configuration
Network resilience settings:
- `RSS_TIMEOUT`: Timeout for RSS fetching (default: 60s)
- `TTS_TIMEOUT`: Timeout for audio generation (default: 900s)
- `RETRY_MAX_ATTEMPTS`: Max retry attempts for failed operations (default: 3)

### Fetcher Rate Limiting
Controls request pacing to avoid overwhelming Nitter:
- `FETCHER_BATCH_SIZE`: Feeds per batch (default: 20)
- `FETCHER_BATCH_DELAY`: Delay between batches (default: 30s)
- `FETCHER_REQUEST_DELAY`: Base delay between requests (default: 5s -> 7.5-12.5s; increase if you see 429 errors)

### Site & Newsletter Website
Controls for the static newsletter site (GitHub Pages):
- `SITE_BASE_URL`: Production domain (e.g. `https://sumbird.ir`). Used for canonical URLs, sitemaps, robots.txt, and Open Graph tags.
- `OG_IMAGE_URL`: Full URL of the default social preview image.

The generated site includes SEO features: canonical URLs, hreflang (en/fa), Schema.org structured data, `og:locale:alternate`, and `robots.txt` with sitemap references. Content lives under `/en/` and `/fa/` (index, `news/<date>/`, pagination pages).

### Prompts Customization
The `prompts/` directory contains AI system prompts for each step:
- `summarizer.txt`: Instructions for summarization
- `translator.txt`: Instructions for translation
- `script_writer.txt`: Instructions for TTS optimization
- `narrator.txt`: Instructions for audio generation
- `headline_writer.txt`: Instructions for Telegram headlines

**Tip:** Customize these prompts to change the AI's behavior, tone, or focus.

## Usage

### Common Commands

**Production Mode:**
```bash
python main.py                      # Full pipeline
python main.py --skip-telegram      # Skip Telegram (testing)
python main.py --skip-tts           # Skip audio generation (faster)
python main.py --date 2025-12-01    # Process specific date
python main.py --force-override     # Regenerate all files (ignore cache)
```

**Test Mode** (uses `test/data/` directories and test Telegram channel):
```bash
python test/test_main.py --skip-telegram
python test/test_main.py --date 2025-12-01
```

**Lock Management** (prevents concurrent pipeline runs):
```bash
python main.py --check-lock         # Check if pipeline is running
python main.py --force-lock         # Force release lock and run
```

**Individual Modules** (for debugging or partial runs; run from repo root):
```bash
python -m src.fetcher               # Step 1: Fetch tweets
python -m src.summarizer            # Step 2: Generate summary
python -m src.translator            # Step 3: Translate to Persian
python -m src.script_writer         # Step 4: Optimize for TTS
python -m src.narrator              # Step 5: Generate audio
python -m src.telegraph_converter   # Step 6: Convert for Telegraph
python -m src.telegraph_publisher   # Step 7: Publish to Telegraph
python -m src.telegram_distributer  # Step 8: Distribute to Telegram
python -m src.newsletter_generator  # Step 9: Generate website
```

**Newsletter regeneration** (full rebuild with current templates):
```bash
python -m src.newsletter_generator --force --en   # Regenerate all English pages
python -m src.newsletter_generator --force --fa  # Regenerate all Farsi pages
```

### Utility Scripts

**Newsletter Preview:**
```bash
cd docs && python -m http.server 8000
# Visit http://localhost:8000/en/ (English) or http://localhost:8000/fa/ (Farsi)
```

**Automated Scheduling** (macOS only):
```bash
./scripts/pipeline_scheduler.sh setup    # Set up cron jobs and wake schedules
./scripts/pipeline_scheduler.sh status   # Check scheduling status
./scripts/pipeline_scheduler.sh test     # Test run without scheduling
./scripts/pipeline_scheduler.sh remove   # Remove all scheduling
```

**Note:** The scheduler uses `pmset` and `caffeinate` (macOS-specific). Linux users should configure `cron` manually.

**Log Analysis:**
```bash
python scripts/daily_runs_generator.py      # Generate daily run statistics
python scripts/handle_counts_generator.py   # Generate handle statistics
```

**Telegraph Management:**
```bash
python scripts/telegraph_post_manager.py    # Manage Telegraph posts
```

## Project Structure

```
.
├── src/                          # Core pipeline modules (9 steps)
│   ├── fetcher.py               # Step 1: Fetch tweets from RSS
│   ├── summarizer.py            # Step 2: AI summarization
│   ├── translator.py            # Step 3: Translation to Persian
│   ├── script_writer.py         # Step 4: TTS optimization
│   ├── narrator.py              # Step 5: Audio generation
│   ├── telegraph_converter.py   # Step 6: Telegraph formatting
│   ├── telegraph_publisher.py   # Step 7: Publish to Telegraph
│   ├── telegram_distributer.py  # Step 8: Telegram distribution
│   └── newsletter_generator.py  # Step 9: Website generation
│
├── utils/                        # Shared utilities
│   ├── env_utils.py             # Environment variable management
│   ├── gemini_utils.py          # Gemini API client
│   ├── openrouter_utils.py      # OpenRouter API client
│   ├── telegraph_utils.py       # Telegraph API client
│   ├── file_utils.py            # File operations
│   ├── date_utils.py            # Date/time handling
│   ├── logging_utils.py         # Centralized logging
│   ├── lock_utils.py            # Pipeline lock mechanism
│   └── retry_utils.py           # Retry logic with exponential backoff
│
├── prompts/                      # AI system prompts (customizable)
│   ├── summarizer.txt           # Summarization instructions
│   ├── translator.txt           # Translation instructions
│   ├── script_writer.txt        # TTS optimization instructions
│   ├── narrator.txt             # Audio generation instructions
│   └── headline_writer.txt      # Telegram headline instructions
│
├── scripts/                      # Utility scripts
│   ├── pipeline_scheduler.sh    # Automated scheduling (macOS)
│   ├── generate_newsletter.py   # Newsletter generation
│   ├── telegraph_post_manager.py # Telegraph management
│   ├── daily_runs_generator.py  # Log analysis
│   └── handle_counts_generator.py # Handle statistics
│
├── test/                         # Test configuration
│   ├── test_main.py             # Test pipeline entry point
│   └── test_config.py           # Test-specific configuration
│
├── data/                         # Pipeline outputs (auto-created)
│   ├── export/                  # Fetched tweets
│   ├── summary/                 # AI summaries
│   ├── translated/              # Translated content
│   ├── script/                  # TTS-optimized scripts
│   ├── narrated/                # Audio files
│   ├── converted/               # Telegraph-formatted content
│   └── published/               # Publication metadata
│
├── docs/                         # Newsletter website (GitHub Pages)
│   ├── index.html               # Redirect to /en/
│   ├── robots.txt               # Crawler rules and sitemap URLs
│   ├── en/                      # English (index, news/<date>/, pageN.html, sitemap, feed)
│   ├── fa/                      # Farsi (index, news/<date>/, pageN.html, sitemap, feed)
│   └── assets/                  # CSS, images, components
│
├── logs/                         # Execution logs (auto-created)
│
├── main.py                       # Pipeline entry point
├── config.py                     # Configuration loader
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Nitter service
├── nitter.conf                   # Nitter configuration
├── sessions.jsonl                # Twitter session tokens
└── .env                          # Environment configuration (create from .env.example)
```

## Development & Testing

### Test Mode
Run the pipeline in an isolated test environment:
```bash
python test/test_main.py --skip-telegram
```

**Test mode differences:**
- Uses `test/data/` directories instead of `data/`
- Uses `TEST_TELEGRAM_CHAT_ID` (separate test channel)
- Adds "TEST-" prefix to titles
- Same Telegraph account (for testing publication)

### Debugging Individual Steps
Each module can be run independently from the repo root:
```bash
python -m src.fetcher              # Test RSS fetching
python -m src.summarizer           # Test AI summarization
python -m src.narrator             # Test audio generation
```

### Cache Behavior
The pipeline caches outputs in `data/` directories:
- If a file exists, it's reused (saves API calls and time)
- Use `--force-override` to regenerate all files

### Lock Mechanism
The pipeline uses a lock file (`logs/example.lock`) to prevent concurrent runs:
- Lock is automatically released on successful completion
- Use `--check-lock` to check status
- Use `--force-lock` to force release (if pipeline crashed)

## Troubleshooting

### Nitter Issues
**Problem:** RSS feeds return empty or error
```bash
# Check if Nitter is running
docker ps

# Check Nitter logs
docker logs nitter

# Verify session tokens are valid
cat sessions.jsonl

# Recreate session tokens if expired
python3 create_session_browser.py <username> <password> --append sessions.jsonl
docker compose restart nitter
```

### Audio Generation Issues
**Problem:** Audio files missing or conversion fails
```bash
# Check if FFmpeg is installed
ffmpeg -version

# If missing, install:
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg
```

**Fallback:** If FFmpeg is unavailable, the pipeline uses Python-based conversion (lower quality) or keeps WAV format.

### Pipeline Lock Issues
**Problem:** "Pipeline is already running" error
```bash
# Check lock status
python main.py --check-lock

# Force release lock (if pipeline crashed)
python main.py --force-lock
```

### API Rate Limiting
**Problem:** API errors or timeouts
- Increase timeout values in `.env` (e.g., `OPENROUTER_TIMEOUT`, `TTS_TIMEOUT`)
- Increase `FETCHER_REQUEST_DELAY` and `FETCHER_BATCH_DELAY` for Nitter
- Check API quota limits

### Missing Dependencies
**Problem:** Import errors or missing modules
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check Python version (requires 3.8+)
python --version
```

## Performance Optimization

### Fetcher Rate Limiting
The fetcher uses configurable delays to avoid overwhelming Nitter:
- Delay between feeds: `FETCHER_REQUEST_DELAY * 1.5` to `* 2.5` seconds (default 5.0 -> 7.5-12.5s)
- Batch delay: `FETCHER_BATCH_DELAY` + 0-15s jitter between batches
- If you see 429 errors, increase `FETCHER_REQUEST_DELAY` (e.g. 12) and `FETCHER_BATCH_DELAY` (e.g. 60)

### Caching Strategy
- Pipeline caches all intermediate outputs
- Run with `--force-override` only when needed (regenerates everything)
- Delete specific files in `data/` directories to regenerate only those steps

### Parallel Testing
Use test mode for development to avoid affecting production data:
```bash
python test/test_main.py --skip-telegram --skip-tts
```

### Skipping Steps
- Use `--skip-telegram` when testing (avoids spamming channel)
- Use `--skip-tts` when audio isn't needed (saves 1-2 minutes per run)

## Automation

### Automated Scheduling (macOS)
Set up daily automated runs:
```bash
./scripts/pipeline_scheduler.sh setup
```

## License

This project is provided as-is for personal and educational use.