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
8. Distributes the content to Telegram channel
"""
import os
import sys
import json
from datetime import datetime

# Ensure environment is loaded before importing config-dependent modules
from utils import env_utils
if not env_utils.env_vars:
    env_utils.load_environment()

# Import utilities from utils package
from utils.file_utils import ensure_directories, get_file_path, file_exists
from utils.date_utils import get_date_str, format_datetime
from utils.logging_utils import log_step, log_pipeline_step, log_info, log_error

# Import configuration
from config import HANDLES, MIN_FEEDS_TOTAL, MIN_FEEDS_SUCCESS_RATIO

# Import pipeline modules
from src.fetcher import fetch_and_format
from src.summarizer import summarize
from src.translator import translate
from src.script_writer import write_scripts
from src.narrator import narrate
from src.telegraph_converter import convert_all_summaries
from src.telegraph_publisher import publish
from src.telegram_distributer import distribute

def run_pipeline():
    """Run the complete pipeline sequentially."""
    # Ensure all directories exist before starting the pipeline
    ensure_directories()
    
    date_str = get_date_str()
    log_info('Pipeline', f"Starting pipeline for date: {date_str}")
    
    # Open log file for this run
    with open(os.path.join('logs', 'log.txt'), 'a', encoding='utf-8') as log_file:
        # Log start time with consistent datetime format
        now = format_datetime()
        log_step(log_file, True, f"Started at {now}")
        
        # Step 1: Fetch and format tweets
        log_pipeline_step("Step 1", "Fetch and Format Tweets")
        
        export_file = get_file_path('export', date_str)
        using_cached_export = os.path.exists(export_file)
        
        if using_cached_export:
            # Using cached export file
            log_info('Pipeline', f"Using existing export file: {export_file}")
            log_step(log_file, True, "Gathered (using cached file)")
            log_step(log_file, True, "Fetched (using cached file)")
            feeds_success = 0  # We don't know the actual count from cached file
            feeds_total = 0
            failed_handles = []
        else:
            # Run the fetcher
            exported_file, feeds_success, feeds_total, failed_handles = fetch_and_format()
            
            if not exported_file or not os.path.exists(exported_file):
                log_error('Pipeline', "Tweet fetching and formatting failed")
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
            
            log_info('Pipeline', f"Tweets fetched and saved to {exported_file}")
        
        # Step 2: Summarize with AI
        log_pipeline_step("Step 2", "Summarize with AI")
        
        summary_file = get_file_path('summary', date_str)
        using_cached_summary = os.path.exists(summary_file)
        
        if using_cached_summary:
            # Using cached summary file
            log_info('Pipeline', f"Using existing summary file: {summary_file}")
            log_step(log_file, True, "Summarized (using cached file)")
            input_tokens = 0
            output_tokens = 0
        else:
            # Run summarization
            summarized_file, input_tokens, output_tokens = summarize()
            
            if not summarized_file or not os.path.exists(summarized_file):
                log_error('Pipeline', "AI summarization failed")
                log_step(log_file, False, "Summarized")
                log_file.write("──────────\n")
                return False
            
            log_info('Pipeline', f"Summary created and saved to {summarized_file}")
            log_step(log_file, True, f"Summarized using {input_tokens} input tokens, {output_tokens} output tokens")
        
        # Step 3: Translate summary to Persian
        log_pipeline_step("Step 3", "Translate Summary to Persian")
        
        translated_file = get_file_path('translated', date_str)
        using_cached_translation = os.path.exists(translated_file)
        
        if using_cached_translation:
            # Using cached translation file
            log_info('Pipeline', f"Using existing translation file: {translated_file}")
            log_step(log_file, True, "Translated (using cached file)")
            tr_input_tokens = 0
            tr_output_tokens = 0
        else:
            # Run translation
            translated_file, tr_input_tokens, tr_output_tokens = translate()
            
            if not translated_file or not os.path.exists(translated_file):
                log_error('Pipeline', "Persian translation failed")
                log_step(log_file, False, "Translated")
                log_file.write("──────────\n")
                return False
            
            log_info('Pipeline', f"Translation created and saved to {translated_file}")
            log_step(log_file, True, f"Translated using {tr_input_tokens} input tokens, {tr_output_tokens} output tokens")
        
        # Step 4: Convert to TTS-optimized Scripts
        log_pipeline_step("Step 4", "Convert to TTS-optimized Scripts")
        
        # Check if script files already exist
        summary_script_path = get_file_path('script', date_str)
        translated_script_path = get_file_path('script', date_str, lang='FA')
        using_cached_scripts = file_exists(summary_script_path) and file_exists(translated_script_path)
        
        if using_cached_scripts:
            log_info('Pipeline', f"Using existing script files: {summary_script_path}, {translated_script_path}")
            log_step(log_file, True, "Scripted (using cached files)")
            sc_input_tokens = 0
            sc_output_tokens = 0
        else:
            # Run script writing
            summary_script, translated_script, sc_input_tokens, sc_output_tokens = write_scripts()
            
            if not summary_script or not translated_script:
                log_error('Pipeline', "Script writing failed")
                log_step(log_file, False, "Scripted")
                log_file.write("──────────\n")
                return False
            
            log_info('Pipeline', f"Scripts created: Summary: {summary_script}, Translation: {translated_script}")
            log_step(log_file, True, f"Scripted using {sc_input_tokens} input tokens, {sc_output_tokens} output tokens")
        
        # Step 5: Convert to Speech (TTS)
        log_pipeline_step("Step 5", "Convert to Speech (TTS)")
        
        # Check if audio files already exist
        summary_audio_path = get_file_path('narrated', date_str)
        translated_audio_path = get_file_path('narrated', date_str, lang='FA')
        using_cached_audio = file_exists(summary_audio_path) and file_exists(translated_audio_path)
        
        if using_cached_audio:
            log_info('Pipeline', f"Using existing audio files: {summary_audio_path}, {translated_audio_path}")
            log_step(log_file, True, f"Narrated (using cached files)")
        else:
            summary_audio, translated_audio = narrate()
            
            # Both audio files are now required
            if summary_audio and translated_audio:
                log_info('Pipeline', f"Audio files created: Summary: {summary_audio}, Translation: {translated_audio}")
                log_step(log_file, True, f"Narrated 2 audio files")
            else:
                log_error('Pipeline', "TTS conversion failed")
                log_step(log_file, False, "Narrated")
                log_file.write("──────────\n")
                return False
        
        # Step 6: Convert to Telegraph format
        log_pipeline_step("Step 6", "Convert to Telegraph Format")
        
        converted = convert_all_summaries()
        if not converted:
            log_error('Pipeline', "Telegraph conversion failed")
            log_step(log_file, False, "Converted to JSON")
            log_file.write("──────────\n")
            return False
        
        # Construct the converted file path since the function now returns a boolean
        converted_file = get_file_path('converted', date_str)
        fa_converted_file = get_file_path('converted', date_str, lang='FA')
        
        if os.path.exists(fa_converted_file):
            log_info('Pipeline', f"Content converted to Telegraph format and saved to {converted_file} and {fa_converted_file}")
        else:
            log_info('Pipeline', f"Content converted to Telegraph format and saved to {converted_file}")
        
        log_step(log_file, True, "Converted to JSON")
        
        # Step 7: Publish to Telegraph
        log_pipeline_step("Step 7", "Publish to Telegraph")
        
        # Pass feeds_success to the publish function
        published_file = publish(feeds_success)
        if not published_file or not os.path.exists(published_file):
            log_error('Pipeline', "Telegraph publishing failed")
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
            log_error('Pipeline', f"Error reading published file: {e}")
        
        log_info('Pipeline', f"Content published and details saved to {published_file}")
        if telegraph_fa_url:
            log_step(log_file, True, f"Published on {telegraph_url} and {telegraph_fa_url}")
        else:
            log_step(log_file, True, f"Published on {telegraph_url}")
        
        # Step 8: Distribute to Telegram Channel
        log_pipeline_step("Step 8", "Distribute to Telegram Channel")
        
        telegram_url = ""
        distribution_success, telegram_url = distribute()
        if not distribution_success:
            log_error('Pipeline', "Telegram distribution failed")
            log_step(log_file, False, "Distributed")
            log_file.write("──────────\n")
            return False
        
        log_info('Pipeline', "Content successfully distributed to Telegram channel")
        log_step(log_file, True, f"Distributed at {telegram_url}")
        
        log_info('Pipeline', "Pipeline completed successfully!")
        log_file.write("──────────\n")
        
        return True

if __name__ == "__main__":
    try:
        success = run_pipeline()
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