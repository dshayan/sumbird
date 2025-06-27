#!/usr/bin/env python3
"""
Test pipeline for Sumbird.

This script runs the complete Sumbird pipeline in test mode, using separate
test directories and a test Telegram channel while maintaining the same
Telegraph account.
"""
import os
import sys
import json
import argparse

# Add parent directory to path to import from main project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure environment is loaded before importing config-dependent modules
from utils import env_utils
if not env_utils.env_vars:
    env_utils.load_environment()

# Import test configuration instead of main config
import test.test_config as config
from utils.logging_utils import log_info, log_error

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Sumbird Test Pipeline - Run pipeline in test mode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test/test_main.py                    # Run complete test pipeline including Telegram distribution
  python test/test_main.py --skip-telegram   # Run test pipeline but skip Telegram distribution step
        """
    )
    
    parser.add_argument(
        '--skip-telegram',
        action='store_true',
        help='Skip the Telegram distribution step (Step 8) in test mode'
    )
    
    return parser.parse_args()

def run_test_pipeline(skip_telegram=False):
    """Run the complete test pipeline."""
    from utils.pipeline_core import run_pipeline_core
    
    return run_pipeline_core(config, log_prefix="TEST ", test_mode=True, skip_telegram=skip_telegram)

if __name__ == "__main__":
    try:
        args = parse_arguments()
        
        if args.skip_telegram:
            log_info('Test Pipeline', "Starting test pipeline with Telegram distribution disabled")
        
        success = run_test_pipeline(skip_telegram=args.skip_telegram)
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