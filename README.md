# Sumbird

AI-powered pipeline for fetching Twitter/X content via RSS, summarizing with AI, translating to Persian, converting to speech, and publishing to Telegraph, Telegram, and newsletter website.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   cp prompts/*.txt.example prompts/*.txt
   # Edit .env with your API keys and settings
   ```

3. **Set up Nitter and session tokens:**
   ```bash
   docker compose up -d
   ./scripts/create_nitter_session.sh
   ```

4. **Run pipeline:**
   ```bash
   python main.py
   ```

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

- **API Keys**: OpenRouter, Gemini, Telegraph, Telegram tokens
- **AI Models**: Model selection and parameters for each pipeline step  
- **Content Sources**: Twitter/X handles to monitor via RSS
- **Output Formatting**: Telegraph and Telegram message formatting
- **Pipeline Settings**: Thresholds, timeouts, and retry configuration

### Nitter Setup
Sumbird uses self-hosted [Nitter](https://github.com/zedeus/nitter) for Twitter/X RSS feeds.

**Setup:**
```bash
docker compose up -d
./scripts/create_nitter_session.sh
docker compose restart nitter
```

**Verify:**
```bash
curl http://localhost:8080/OpenAI/rss
```

**Troubleshooting:**
- Services not running: `docker compose logs`
- Session issues: `docker logs nitter`
- RSS errors: Session tokens invalid/expired - create new ones

## Usage

### Pipeline Commands
```bash
# Complete pipeline
python main.py
python main.py --skip-telegram
python main.py --force-override

# Test pipeline (isolated test/data/ directories)
python test/test_main.py
python test/test_main.py --skip-telegram
python test/test_main.py --force-override
```

### Individual Modules
```bash
python src/fetcher.py                # Fetch tweets
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
# Newsletter management
python scripts/generate_newsletter.py --no-commit
python scripts/generate_newsletter.py

# Telegraph post management
python scripts/telegraph_post_manager.py

# Session token creation
./scripts/create_nitter_session.sh

# Automated scheduling
./scripts/pipeline_scheduler.sh setup
./scripts/pipeline_scheduler.sh remove
./scripts/pipeline_scheduler.sh status
./scripts/pipeline_scheduler.sh test

# Development tools
python scripts/fetcher_monitor.py    # HTTP traffic monitoring
python scripts/fetcher_original.py   # Alternative RSS fetcher
```

### Pipeline Flow
Fetch → Summarize → Translate → Script → Narrate → Convert → Publish → Distribute → Newsletter

### Development
```bash
# Preview newsletter locally
cd docs && python -m http.server 8000
# Visit http://localhost:8000/en/ (English) or http://localhost:8000/fa/ (Farsi)
# Root (http://localhost:8000) redirects to /en/
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