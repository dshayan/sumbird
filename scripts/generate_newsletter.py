#!/usr/bin/env python3
"""
Standalone script to generate the newsletter website from summary files.

This script can be used to:
1. Generate the newsletter website manually
2. Test the newsletter generation without running the full pipeline
3. Regenerate the website from existing summary files

Usage:
    python scripts/generate_newsletter.py                    # Generate and commit
    python scripts/generate_newsletter.py --no-commit       # Generate without committing
    python scripts/generate_newsletter.py --web-repo PATH   # Use custom web repo path
"""
import os
import sys
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Ensure environment is loaded
from utils import env_utils
if not env_utils.env_vars:
    env_utils.load_environment()

from src.newsletter_generator import NewsletterGenerator
from utils.logging_utils import log_info, log_error, log_success

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate Sumbird website from summary files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_newsletter.py                           # Generate and auto-commit
  python scripts/generate_newsletter.py --no-commit              # Generate without committing
  python scripts/generate_newsletter.py --docs-path ./my-docs    # Use custom docs path
        """
    )
    
    parser.add_argument(
        '--no-commit',
        action='store_true',
        help='Generate website but do not commit and push changes'
    )
    
    parser.add_argument(
        '--docs-path',
        type=str,
        help='Path to the docs directory (default: ./docs)'
    )
    
    return parser.parse_args()

def main():
    """Main function."""
    try:
        args = parse_arguments()
        
        log_info("Newsletter Script", "Starting newsletter generation...")
        
        # Initialize generator with external CSS
        if args.docs_path:
            generator = NewsletterGenerator(args.docs_path, use_external_css=True)
        else:
            generator = NewsletterGenerator(use_external_css=True)
        
        # Generate newsletter
        auto_commit = not args.no_commit
        success = generator.generate_newsletter(auto_commit=auto_commit)
        
        if success:
            if auto_commit:
                log_success("Newsletter Script", "Newsletter generated and committed successfully!")
            else:
                log_success("Newsletter Script", "Newsletter generated successfully (not committed)")
        else:
            log_error("Newsletter Script", "Newsletter generation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        log_info("Newsletter Script", "Newsletter generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error("Newsletter Script", f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()