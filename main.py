#!/usr/bin/env python3
"""
Main entry point for Sumbird - Twitter/X RSS feed fetcher, summarizer and publisher.

This pipeline:
1. Fetches tweets from specified handles for a target date and formats them
2. Processes them with AI (via OpenRouter) to generate a summary
3. Translates the summary to Persian
4. Converts the summary to Telegraph format
5. Publishes the content to Telegraph
6. Distributes the content to Telegram channel
"""
import os
import sys
import json
from datetime import datetime

# Import utilities from utils package
from utils.file_utils import ensure_directories, get_file_path
from utils.date_utils import get_date_str, format_datetime
from utils.logging_utils import log_step

# Import configuration
from config import HANDLES, MIN_FEEDS_TOTAL, MIN_FEEDS_SUCCESS_RATIO

# Import pipeline modules
from src.fetcher import fetch_and_format
from src.summarizer import summarize
from src.translator import translate
from src.telegraph_converter import convert_all_summaries
from src.telegraph_publisher import publish
from src.telegram_distributer import distribute

def run_pipeline():
    """Run the complete pipeline sequentially."""
    # Ensure all directories exist before starting the pipeline
    ensure_directories()
    
    date_str = get_date_str()
    print(f"Starting pipeline for date: {date_str}")
    
    # Open log file for this run
    with open(os.path.join('logs', 'log.txt'), 'a', encoding='utf-8') as log_file:
        # Log start time with consistent datetime format
        now = format_datetime()
        log_step(log_file, True, f"Started at {now}")
        
        # Step 1: Fetch and format tweets
        print("\n=== Step 1: Fetch and Format Tweets ===")
        
        export_file = get_file_path('export', date_str)
        using_cached_export = os.path.exists(export_file)
        
        if using_cached_export:
            # Using cached export file
            print(f"Using existing export file: {export_file}")
            log_step(log_file, True, "Gathered (using cached file)")
            log_step(log_file, True, "Fetched (using cached file)")
            feeds_success = 0  # We don't know the actual count from cached file
            feeds_total = 0
            failed_handles = []
        else:
            # Run the fetcher
            exported_file, feeds_success, feeds_total, failed_handles = fetch_and_format()
            
            if not exported_file or not os.path.exists(exported_file):
                print("Error: Tweet fetching and formatting failed")
                log_step(log_file, False, f"Gathered {feeds_total} sources")
                
                # Building the failed handles string
                failed_str = ""
                if failed_handles and len(failed_handles) > 0:
                    failed_str = f" (Failed: {', '.join(failed_handles)})"
                
                log_step(log_file, False, f"Fetched {feeds_success}/{feeds_total} sources{failed_str}")
                log_file.write("──────────\n")
                return False
            
            # Logging gather success (considered successful if > MIN_FEEDS_TOTAL sources)
            gather_success = feeds_total > MIN_FEEDS_TOTAL
            log_step(log_file, gather_success, f"Gathered {feeds_total} sources")
            
            # Logging fetch success (considered successful if fetched/gathered >= MIN_FEEDS_SUCCESS_RATIO)
            fetch_success = (feeds_success / feeds_total >= MIN_FEEDS_SUCCESS_RATIO) if feeds_total > 0 else False
            
            # Building the failed handles string
            failed_str = ""
            if failed_handles and len(failed_handles) > 0:
                failed_str = f" (Failed: {', '.join(failed_handles)})"
            
            log_step(log_file, fetch_success, f"Fetched {feeds_success}/{feeds_total} sources{failed_str}")
            
            print(f"Tweets fetched and saved to {exported_file}")
        
        # Step 2: Summarize with AI
        print("\n=== Step 2: Summarize with AI ===")
        
        summary_file = get_file_path('summary', date_str)
        using_cached_summary = os.path.exists(summary_file)
        
        if using_cached_summary:
            # Using cached summary file
            print(f"Using existing summary file: {summary_file}")
            log_step(log_file, True, "Summarized (using cached file)")
            input_tokens = 0
            output_tokens = 0
        else:
            # Run summarization
            summarized_file, input_tokens, output_tokens = summarize()
            
            if not summarized_file or not os.path.exists(summarized_file):
                print("Error: AI summarization failed")
                log_step(log_file, False, "Summarized")
                log_file.write("──────────\n")
                return False
            
            print(f"Summary created and saved to {summarized_file}")
            log_step(log_file, True, f"Summarized using {input_tokens} input tokens, {output_tokens} output tokens")
        
        # Step 3: Translate summary to Persian
        print("\n=== Step 3: Translate Summary to Persian ===")
        
        translated_file = get_file_path('translated', date_str)
        using_cached_translation = os.path.exists(translated_file)
        
        if using_cached_translation:
            # Using cached translation file
            print(f"Using existing translation file: {translated_file}")
            log_step(log_file, True, "Translated (using cached file)")
            tr_input_tokens = 0
            tr_output_tokens = 0
        else:
            # Run translation
            translated_file, tr_input_tokens, tr_output_tokens = translate()
            
            if not translated_file or not os.path.exists(translated_file):
                print("Warning: Persian translation failed, continuing with English only")
                log_step(log_file, False, "Translated")
            else:
                print(f"Translation created and saved to {translated_file}")
                log_step(log_file, True, f"Translated using {tr_input_tokens} input tokens, {tr_output_tokens} output tokens")
        
        # Step 4: Convert to Telegraph format
        print("\n=== Step 4: Convert to Telegraph Format ===")
        
        converted = convert_all_summaries()
        if not converted:
            print("Error: Telegraph conversion failed")
            log_step(log_file, False, "Converted to JSON")
            log_file.write("──────────\n")
            return False
        
        # Construct the converted file path since the function now returns a boolean
        converted_file = get_file_path('converted', date_str)
        fa_converted_file = get_file_path('converted', date_str, lang='FA')
        
        if os.path.exists(fa_converted_file):
            print(f"Content converted to Telegraph format and saved to {converted_file} and {fa_converted_file}")
        else:
            print(f"Content converted to Telegraph format and saved to {converted_file}")
        
        log_step(log_file, True, "Converted to JSON")
        
        # Step 5: Publish to Telegraph
        print("\n=== Step 5: Publish to Telegraph ===")
        
        # Pass feeds_success to the publish function
        published_file = publish(feeds_success)
        if not published_file or not os.path.exists(published_file):
            print("Error: Telegraph publishing failed")
            log_step(log_file, False, "Published")
            log_file.write("──────────\n")
            return False
        
        # Read the published file to get the URLs
        telegraph_url = ""
        telegraph_fa_url = ""
        try:
            with open(published_file, 'r', encoding='utf-8') as f:
                published_data = json.load(f)
                telegraph_url = published_data.get("url", "")
                telegraph_fa_url = published_data.get("fa_url", "")
        except Exception as e:
            print(f"Error reading published file: {e}")
        
        print(f"Content published and details saved to {published_file}")
        if telegraph_fa_url:
            log_step(log_file, True, f"Published on {telegraph_url} and {telegraph_fa_url}")
        else:
            log_step(log_file, True, f"Published on {telegraph_url}")
        
        # Step 6: Distribute to Telegram Channel
        print("\n=== Step 6: Distribute to Telegram Channel ===")
        
        telegram_url = ""
        distribution_success, telegram_url = distribute()
        if not distribution_success:
            print("Error: Telegram distribution failed")
            log_step(log_file, False, "Distributed")
            log_file.write("──────────\n")
            return False
        
        print("Content successfully distributed to Telegram channel")
        log_step(log_file, True, f"Distributed at {telegram_url}")
        
        print("Pipeline completed successfully!")
        log_file.write("──────────\n")
        
        return True

if __name__ == "__main__":
    try:
        success = run_pipeline()
        if success:
            print("Pipeline execution completed")
        else:
            print("Pipeline execution failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1) 