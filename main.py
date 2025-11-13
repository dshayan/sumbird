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
import argparse
import json
import os
import sys
from datetime import datetime

# Ensure environment is loaded before importing config-dependent modules
from utils import env_utils
if not env_utils.env_vars:
    env_utils.load_environment()

from utils.lock_utils import PipelineLock, check_lock_status, force_release_lock
from utils.logging_utils import log_error, log_info

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Sumbird Pipeline - Twitter/X RSS feed fetcher, summarizer and publisher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run complete pipeline including Telegram distribution
  python main.py --skip-telegram   # Run pipeline but skip Telegram distribution step
  python main.py --skip-tts        # Run pipeline but skip TTS steps (Script Writer and Narrator)
  python main.py --force-lock     # Force release any existing lock and run pipeline
  python main.py --check-lock     # Check lock status without running pipeline
  python main.py --force-override # Force regeneration of all files, bypassing cache
        """
    )
    
    parser.add_argument(
        '--skip-telegram',
        action='store_true',
        help='Skip the Telegram distribution step (Step 8)'
    )
    
    parser.add_argument(
        '--skip-tts',
        action='store_true',
        help='Skip the TTS steps (Script Writer and Narrator - Steps 4 and 5)'
    )
    
    parser.add_argument(
        '--force-lock',
        action='store_true',
        help='Force release any existing lock before running pipeline'
    )
    
    parser.add_argument(
        '--check-lock',
        action='store_true',
        help='Check lock status and exit without running pipeline'
    )
    
    parser.add_argument(
        '--force-override',
        action='store_true',
        help='Force regeneration of all files, bypassing cache and overriding existing outputs'
    )
    
    return parser.parse_args()

def run_pipeline(skip_telegram=False, skip_tts=False, force_override=False):
    """Run the complete pipeline sequentially."""
    import config
    from utils.pipeline_core import run_pipeline_core
    
    return run_pipeline_core(config, skip_telegram=skip_telegram, skip_tts=skip_tts, force_override=force_override)

if __name__ == "__main__":
    try:
        args = parse_arguments()
        
        # Handle lock status check
        if args.check_lock:
            lock_status = check_lock_status()
            print(f"Lock Status: {lock_status['message']}")
            sys.exit(0 if not lock_status['locked'] else 1)
        
        # Handle force lock release
        if args.force_lock:
            if force_release_lock():
                log_info('Pipeline', "Existing lock force-released")
            else:
                log_info('Pipeline', "No existing lock found")
        
        # Run pipeline with lock protection
        with PipelineLock():
            if args.skip_telegram:
                log_info('Pipeline', "Starting pipeline with Telegram distribution disabled")
            if args.skip_tts:
                log_info('Pipeline', "Starting pipeline with TTS steps disabled (Script Writer and Narrator)")
            if args.force_override:
                log_info('Pipeline', "Starting pipeline with force override enabled - all files will be regenerated")
            
            success = run_pipeline(skip_telegram=args.skip_telegram, skip_tts=args.skip_tts, force_override=args.force_override)
            if success:
                log_info('Pipeline', "Pipeline execution completed")
            else:
                log_error('Pipeline', "Pipeline execution failed")
                sys.exit(1)
                
    except RuntimeError as e:
        if "Could not acquire pipeline lock" in str(e):
            lock_status = check_lock_status()
            log_error('Pipeline', f"Pipeline is already running: {lock_status['message']}")
            log_error('Pipeline', "Use --force-lock to override or --check-lock to see status")
        else:
            log_error('Pipeline', f"Runtime error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        log_info('Pipeline', "Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error('Pipeline', f"Unexpected error: {e}")
        sys.exit(1) 