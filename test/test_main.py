#!/usr/bin/env python3
"""
Test pipeline for Sumbird.

This script runs the complete Sumbird pipeline in test mode, using separate
test directories and a test Telegram channel while maintaining the same
Telegraph account.
"""
import argparse
import json
import os
import sys

# Add parent directory to path to import from main project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure environment is loaded before importing config-dependent modules
from utils import env_utils
if not env_utils.env_vars:
    env_utils.load_environment()

import test.test_config as config
from utils.logging_utils import log_error, log_info

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Sumbird Test Pipeline - Run pipeline in test mode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test/test_main.py                    # Run complete test pipeline including Telegram distribution
  python test/test_main.py --skip-telegram   # Run test pipeline but skip Telegram distribution step
  python test/test_main.py --skip-tts        # Run test pipeline but skip TTS steps (Script Writer and Narrator)
  python test/test_main.py --force-override # Force regeneration of all files in test mode
        """
    )
    
    parser.add_argument(
        '--skip-telegram',
        action='store_true',
        help='Skip the Telegram distribution step (Step 8) in test mode'
    )
    
    parser.add_argument(
        '--skip-tts',
        action='store_true',
        help='Skip the TTS steps (Script Writer and Narrator - Steps 4 and 5) in test mode'
    )
    
    parser.add_argument(
        '--force-override',
        action='store_true',
        help='Force regeneration of all files, bypassing cache and overriding existing outputs in test mode'
    )
    
    return parser.parse_args()

def run_test_pipeline(skip_telegram=False, skip_tts=False, force_override=False):
    """Run the complete test pipeline."""
    from utils.pipeline_core import run_pipeline_core
    
    return run_pipeline_core(config, log_prefix="TEST ", test_mode=True, skip_telegram=skip_telegram, skip_tts=skip_tts, force_override=force_override)

if __name__ == "__main__":
    try:
        args = parse_arguments()
        
        if args.skip_telegram:
            log_info('Test Pipeline', "Starting test pipeline with Telegram distribution disabled")
        if args.skip_tts:
            log_info('Test Pipeline', "Starting test pipeline with TTS steps disabled (Script Writer and Narrator)")
        if args.force_override:
            log_info('Test Pipeline', "Starting test pipeline with force override enabled - all files will be regenerated")
        
        success = run_test_pipeline(skip_telegram=args.skip_telegram, skip_tts=args.skip_tts, force_override=args.force_override)
        if success:
            log_info('Test Pipeline', "Test pipeline execution completed")
        else:
            log_error('Test Pipeline', "Test pipeline execution failed")
            sys.exit(1)
    except KeyboardInterrupt:
        log_info('Test Pipeline', "Test pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error('Test Pipeline', f"Unexpected error in test pipeline: {e}")
        sys.exit(1) 