# Sumbird

A comprehensive AI-powered pipeline for fetching tweets from Twitter/X via RSS, summarizing them with AI, translating to Persian, converting to speech, publishing to Telegraph and Telegram, and generating a newsletter website.

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment: `cp .env.example .env` and edit as needed
4. Set up prompt files: `cp prompts/*.txt.example prompts/*.txt` and customize as needed
5. Set up Nitter with Docker (see [Nitter Setup](#nitter-setup) section below)
6. Configure Twitter session tokens (see [Session Configuration](#session-configuration) section below)

## Configuration

All configuration is managed through environment variables. Copy `.env.example` to `.env` and configure:

- **API Keys**: OpenRouter, Gemini, Telegraph, Telegram tokens
- **AI Models**: Model selection and parameters for each pipeline step  
- **Content Sources**: Twitter/X handles to monitor via RSS
- **Output Formatting**: Telegraph and Telegram message formatting
- **Pipeline Settings**: Thresholds, timeouts, and retry configuration

## Nitter Setup

Sumbird uses a self-hosted [Nitter](https://github.com/zedeus/nitter) instance to fetch Twitter/X content via RSS feeds. Nitter is an alternative Twitter front-end that provides privacy-focused access to Twitter content.

### Quick Start

1. **Start Nitter with Docker:**
   ```bash
   docker compose up -d
   ```

2. **Configure session tokens:**
   - **Use the provided script** (recommended):
     ```bash
     ./scripts/create_nitter_session.sh
     ```
   - **Manual configuration**: Create `sessions.jsonl` with your Twitter OAuth tokens:
     ```json
     {"oauth_token": "your_oauth_token", "oauth_token_secret": "your_oauth_token_secret"}
     ```
   - **Restart Nitter**: `docker compose restart nitter`

3. **Verify setup:**
   ```bash
   # Test Nitter RSS feeds manually
   curl http://localhost:8080/OpenAI/rss
   ```

### ARM64 Support

For Apple Silicon users, the Docker setup uses platform emulation. For native ARM64 support, see the [Nitter installation guide](https://github.com/zedeus/nitter#installation).

### Troubleshooting

- **Services not running:** `docker compose logs`
- **Redis connection issues:** `docker compose restart nitter-redis`
- **Port conflicts:** Modify port in `docker-compose.yml` and update `src/fetcher.py`
- **Session token issues:** 
  - Check Nitter logs: `docker logs nitter`
  - If you see "no sessions available", run `./scripts/create_nitter_session.sh`
  - Restart Nitter after updating tokens: `docker compose restart nitter`
- **RSS feeds returning HTML errors:** Session tokens are invalid/expired - create new ones

### Configuration Notes

- Use sectioned format in `nitter.conf`: `[Server]`, `[Cache]`, `[Config]`, `[Preferences]`
- Set `redisHost = "nitter-redis"` in the `[Cache]` section for Docker
- Nitter listens on `0.0.0.0:8080`; mapped to `localhost:8080`

## Session Configuration

Sumbird requires Twitter session tokens to access Twitter content through Nitter. These tokens are stored in `sessions.jsonl`.

### Creating Session Tokens

1. **Use the provided script** (recommended):
   ```bash
   # Run the interactive session creator
   ./scripts/create_nitter_session.sh
   ```
2. **Manual configuration**: Create `sessions.jsonl` with your OAuth tokens:
   ```json
   {"oauth_token": "your_oauth_token", "oauth_token_secret": "your_oauth_token_secret"}
   ```
3. **Follow the official guide**: [Creating session tokens](https://github.com/zedeus/nitter/wiki/Creating-session-tokens)

### Session Management

- **Multiple accounts**: Add multiple lines to `sessions.jsonl` (one JSON object per line)
- **Token rotation**: Replace expired tokens in `sessions.jsonl` or run the script again
- **Security**: Keep `sessions.jsonl` private and add to `.gitignore`
- **Troubleshooting**: If fetcher fails with "mismatched tag" errors, session tokens are invalid/expired

### Token Requirements

- **2FA Secret**: Base32-encoded secret from authenticator app (A-Z, 2-7 only)
- **Not 6-digit codes**: Use the secret key that generates codes, not the codes themselves

## Usage

### Complete Pipeline
```bash
# Run complete pipeline
python main.py

# Run pipeline without Telegram distribution
python main.py --skip-telegram

# Force regeneration of all files (bypass cache)
python main.py --force-override
```

### Test Pipeline
```bash
# Run test pipeline with test configuration
python test/test_main.py

# Run test pipeline without Telegram distribution
python test/test_main.py --skip-telegram

# Force regeneration of all files in test mode
python test/test_main.py --force-override

# Test configuration settings
python test/test_config.py
```

**Test Mode Features:**
- Isolated `test/data/` subdirectories
- Separate `TEST_TELEGRAM_CHAT_ID` for Telegram
- "TEST-" prefix for Telegraph URLs
- Inherits AI model configurations
- Safe testing without affecting production

### Individual Modules
```bash
# Core pipeline modules (run independently)
python src/fetcher.py                # Fetch tweets from self-hosted Nitter RSS feeds
python src/summarizer.py             # Generate AI summaries
python src/translator.py             # Translate to Persian
python src/script_writer.py          # Optimize for text-to-speech
python src/narrator.py               # Generate audio files
python src/telegraph_converter.py    # Convert for Telegraph
python src/telegraph_publisher.py    # Publish to Telegraph
python src/telegram_distributer.py   # Distribute to Telegram
python src/newsletter_generator.py   # Generate newsletter website
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
python scripts/fetcher_monitor.py    # Captures HTTP requests/responses for debugging

# Run original fetcher (alternative RSS source)
python scripts/fetcher_original.py   # Alternative RSS fetcher (non-Nitter)

# Create Nitter session tokens (fixes authentication issues)
./scripts/create_nitter_session.sh

# Set up automated pipeline scheduling (wake + cron)
./scripts/pipeline_scheduler.sh setup

# Remove automated scheduling
./scripts/pipeline_scheduler.sh remove

# Check scheduling status
./scripts/pipeline_scheduler.sh status

# Test run the pipeline
./scripts/pipeline_scheduler.sh test
```

### Pipeline Flow

1. **Fetch** (`src/fetcher.py`): Retrieve tweets via self-hosted Nitter RSS feeds and format into markdown files
2. **Summarize** (`src/summarizer.py`): Generate AI summary using OpenRouter/Claude
3. **Translate** (`src/translator.py`): Convert to Persian using Gemini
4. **Script** (`src/script_writer.py`): Optimize content for text-to-speech
5. **Narrate** (`src/narrator.py`): Generate audio files using Gemini TTS
6. **Convert** (`src/telegraph_converter.py`): Format content for Telegraph
7. **Publish** (`src/telegraph_publisher.py`): Create Telegraph posts
8. **Distribute** (`src/telegram_distributer.py`): Share to Telegram with audio files
9. **Newsletter** (`src/newsletter_generator.py`): Generate website and publish to GitHub Pages

### Newsletter & Development

```bash
# Generate newsletter manually
python scripts/generate_newsletter.py --no-commit  # Without committing
python scripts/generate_newsletter.py            # With auto-commit

# Preview locally
cd docs && python -m http.server 8000
# Visit http://localhost:8000
```

## Project Structure

```
sumbird/
├── src/                    # Core pipeline modules
├── utils/                  # Utility functions  
├── docs/                   # Newsletter website (GitHub Pages)
├── scripts/                # Utility scripts
├── test/                   # Test pipeline and configuration
├── data/                   # Pipeline outputs (auto-created)
├── logs/                   # Execution logs (auto-created)
├── prompts/                # AI system prompts
├── main.py                 # Pipeline entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker services for Nitter
├── nitter.conf             # Nitter configuration
├── sessions.jsonl          # Twitter session tokens
└── .env.example            # Environment configuration template
```