#!/usr/bin/env python3
"""
Main entry point for Sumbird - Twitter/X RSS feed fetcher, summarizer and publisher.

This pipeline:
1. Fetches tweets from specified handles for a target date and formats them
2. Processes them with AI (via OpenRouter) to generate a summary
3. Translates the summary to Persian
4. Converts content to TTS-optimized scripts
5. Converts scripts to speech using TTS
6. Converts the summary to Telegraph format
7. Publishes the content to Telegraph
8. Distributes the content to Telegram channel (optional with --skip-telegram)
9. Generates newsletter website and pushes to GitHub Pages
"""
import os
import sys
import json
import argparse
from datetime import datetime

# Ensure environment is loaded before importing config-dependent modules
from utils import env_utils
if not env_utils.env_vars:
    env_utils.load_environment()

# Import utilities from utils package
from utils.logging_utils import log_info, log_error

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Sumbird Pipeline - Twitter/X RSS feed fetcher, summarizer and publisher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run complete pipeline including Telegram distribution
  python main.py --skip-telegram   # Run pipeline but skip Telegram distribution step
        """
    )
    
    parser.add_argument(
        '--skip-telegram',
        action='store_true',
        help='Skip the Telegram distribution step (Step 8)'
    )
    
    return parser.parse_args()

def run_pipeline(skip_telegram=False):
    """Run the complete pipeline sequentially."""
    import config
    from utils.pipeline_core import run_pipeline_core
    
    return run_pipeline_core(config, skip_telegram=skip_telegram)

if __name__ == "__main__":
    try:
        args = parse_arguments()
        
        if args.skip_telegram:
            log_info('Pipeline', "Starting pipeline with Telegram distribution disabled")
        
        success = run_pipeline(skip_telegram=args.skip_telegram)
        if success:
            log_info('Pipeline', "Pipeline execution completed")
        else:
            log_error('Pipeline', "Pipeline execution failed")
            sys.exit(1)
    except KeyboardInterrupt:
        log_info('Pipeline', "Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error('Pipeline', f"Unexpected error: {e}")
        sys.exit(1) 