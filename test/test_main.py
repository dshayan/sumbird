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

# Add parent directory to path to import from main project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure environment is loaded before importing config-dependent modules
from utils import env_utils
if not env_utils.env_vars:
    env_utils.load_environment()

# Import test configuration instead of main config
import test.test_config as config
from utils.date_utils import get_date_str, format_datetime
from utils.logging_utils import log_step, log_pipeline_step, log_info, log_error
from utils.file_utils import file_exists

# Import pipeline modules
from src import fetcher, summarizer, translator, script_writer, narrator, telegraph_converter, telegraph_publisher, telegram_distributer

def ensure_test_directories():
    """Ensure all test directories exist before starting the pipeline."""
    test_dirs = [
        "test/data/export",
        "test/data/summary", 
        "test/data/translated",
        "test/data/script",
        "test/data/converted",
        "test/data/published",
        "test/data/narrated",
        "logs"  # Logs directory is shared
    ]
    
    for directory in test_dirs:
        os.makedirs(directory, exist_ok=True)

def run_test_pipeline():
    """Run the complete test pipeline."""
    # Ensure all test directories exist before starting the pipeline
    ensure_test_directories()
    
    date_str = get_date_str()
    log_info('Test Pipeline', f"Starting test pipeline for date: {date_str}")
    
    # Open log file for this run (shared with main pipeline)
    with open(os.path.join('logs', 'log.txt'), 'a', encoding='utf-8') as log_file:
        # Log start time with consistent datetime format
        now = format_datetime()
        log_step(log_file, True, f"TEST Started at {now}")
        
        # Step 1: Fetch and format tweets
        log_pipeline_step("Step 1", "Fetch and Format Tweets")
        
        export_file = config.get_file_path('export', date_str)
        using_cached_export = os.path.exists(export_file)
        
        if using_cached_export:
            # Using cached export file
            log_info('Test Pipeline', f"Using existing export file: {export_file}")
            log_step(log_file, True, "TEST Gathered (using cached file)")
            log_step(log_file, True, "TEST Fetched (using cached file)")
            feeds_success = 0  # We don't know the actual count from cached file
            feeds_total = 0
            failed_handles = []
        else:
            # Override the fetcher's file path function
            original_get_file_path = fetcher.get_file_path
            fetcher.get_file_path = config.get_file_path
            
            exported_file, feeds_success, feeds_total, failed_handles = fetcher.fetch_and_format()
            
            # Restore original function
            fetcher.get_file_path = original_get_file_path
            
            if not exported_file or not os.path.exists(exported_file):
                log_error('Test Pipeline', "Tweet fetching and formatting failed")
                log_step(log_file, False, f"TEST Gathered {feeds_total} sources")
                
                # Building the failed handles string
                failed_str = ""
                if failed_handles and len(failed_handles) > 0:
                    failed_str = f" (Failed: {', '.join(failed_handles)})"
                
                log_step(log_file, False, f"TEST Fetched {feeds_success}/{feeds_total} sources{failed_str}")
                log_file.write("──────────\n")
                return False
            
            # Logging gather success (considered successful if > MIN_FEEDS_TOTAL sources)
            gather_success = feeds_total > config.MIN_FEEDS_TOTAL
            log_step(log_file, gather_success, f"TEST Gathered {feeds_total} sources")
            
            # Logging fetch success (considered successful if fetched/gathered >= MIN_FEEDS_SUCCESS_RATIO)
            fetch_success = (feeds_success / feeds_total >= config.MIN_FEEDS_SUCCESS_RATIO) if feeds_total > 0 else False
            
            # Building the failed handles string
            failed_str = ""
            if failed_handles and len(failed_handles) > 0:
                failed_str = f" (Failed: {', '.join(failed_handles)})"
            
            log_step(log_file, fetch_success, f"TEST Fetched {feeds_success}/{feeds_total} sources{failed_str}")
            
            log_info('Test Pipeline', f"Tweets fetched and saved to {exported_file}")
        
        # Step 2: Summarize with AI
        log_pipeline_step("Step 2", "Summarize with AI")
        
        summary_file = config.get_file_path('summary', date_str)
        using_cached_summary = os.path.exists(summary_file)
        
        if using_cached_summary:
            # Using cached summary file
            log_info('Test Pipeline', f"Using existing summary file: {summary_file}")
            log_step(log_file, True, "TEST Summarized (using cached file)")
            input_tokens = 0
            output_tokens = 0
        else:
            # Override the summarizer's file path function and title format
            original_get_file_path = summarizer.get_file_path
            original_summary_title_format = summarizer.SUMMARY_TITLE_FORMAT
            summarizer.get_file_path = config.get_file_path
            summarizer.SUMMARY_TITLE_FORMAT = config.SUMMARY_TITLE_FORMAT
            
            summarized_file, input_tokens, output_tokens = summarizer.summarize()
            
            # Restore original functions
            summarizer.get_file_path = original_get_file_path
            summarizer.SUMMARY_TITLE_FORMAT = original_summary_title_format
            
            if not summarized_file or not os.path.exists(summarized_file):
                log_error('Test Pipeline', "AI summarization failed")
                log_step(log_file, False, "TEST Summarized")
                log_file.write("──────────\n")
                return False
            
            log_info('Test Pipeline', f"Summary created and saved to {summarized_file}")
            log_step(log_file, True, f"TEST Summarized using {input_tokens} input tokens, {output_tokens} output tokens")
        
        # Step 3: Translate summary to Persian
        log_pipeline_step("Step 3", "Translate Summary to Persian")
        
        translated_file = config.get_file_path('translated', date_str)
        using_cached_translation = os.path.exists(translated_file)
        
        if using_cached_translation:
            # Using cached translation file
            log_info('Test Pipeline', f"Using existing translation file: {translated_file}")
            log_step(log_file, True, "TEST Translated (using cached file)")
            tr_input_tokens = 0
            tr_output_tokens = 0
        else:
            # Override the translator's file path function
            original_get_file_path = translator.get_file_path
            translator.get_file_path = config.get_file_path
            
            translated_file, tr_input_tokens, tr_output_tokens = translator.translate()
            
            # Restore original function
            translator.get_file_path = original_get_file_path
            
            # Add TEST- prefix to Persian title
            if translated_file and os.path.exists(translated_file):
                with open(translated_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add TEST- prefix to the Persian title (assuming it starts with <h1>)
                if content.startswith('<h1>'):
                    # Find the end of the h1 tag
                    h1_end = content.find('</h1>')
                    if h1_end != -1:
                        # Extract the title content
                        title_start = content.find('>') + 1
                        title_content = content[title_start:h1_end]
                        # Add TEST- prefix to the Persian title
                        new_title = f"TEST-{title_content}"
                        # Replace the title in the content
                        content = content[:title_start] + new_title + content[h1_end:]
                        
                        # Write the modified content back
                        with open(translated_file, 'w', encoding='utf-8') as f:
                            f.write(content)
            
            if not translated_file or not os.path.exists(translated_file):
                log_error('Test Pipeline', "Persian translation failed")
                log_step(log_file, False, "TEST Translated")
                log_file.write("──────────\n")
                return False
            
            log_info('Test Pipeline', f"Translation created and saved to {translated_file}")
            log_step(log_file, True, f"TEST Translated using {tr_input_tokens} input tokens, {tr_output_tokens} output tokens")
        
        # Step 4: Convert to TTS-optimized Scripts
        log_pipeline_step("Step 4", "Convert to TTS-optimized Scripts")
        
        # Check if script files already exist
        summary_script_path = config.get_file_path('script', date_str)
        translated_script_path = config.get_file_path('script', date_str, lang='FA')
        using_cached_scripts = file_exists(summary_script_path) and file_exists(translated_script_path)
        
        if using_cached_scripts:
            log_info('Test Pipeline', f"Using existing script files: {summary_script_path}, {translated_script_path}")
            log_step(log_file, True, "TEST Scripted (using cached files)")
            sc_input_tokens = 0
            sc_output_tokens = 0
        else:
            # Override the script_writer's file path function
            original_get_file_path = script_writer.get_file_path
            script_writer.get_file_path = config.get_file_path
            
            summary_script, translated_script, sc_input_tokens, sc_output_tokens = script_writer.write_scripts()
            
            # Restore original function
            script_writer.get_file_path = original_get_file_path
            
            if not summary_script or not translated_script:
                log_error('Test Pipeline', "Script writing failed")
                log_step(log_file, False, "TEST Scripted")
                log_file.write("──────────\n")
                return False
            
            log_info('Test Pipeline', f"Scripts created: Summary: {summary_script}, Translation: {translated_script}")
            log_step(log_file, True, f"TEST Scripted using {sc_input_tokens} input tokens, {sc_output_tokens} output tokens")
        
        # Step 5: Convert to Speech (TTS)
        log_pipeline_step("Step 5", "Convert to Speech (TTS)")
        
        # Check if audio files already exist
        summary_audio_path = config.get_file_path('narrated', date_str)
        translated_audio_path = config.get_file_path('narrated', date_str, lang='FA')
        using_cached_audio = file_exists(summary_audio_path) and file_exists(translated_audio_path)
        
        if using_cached_audio:
            log_info('Test Pipeline', f"Using existing audio files: {summary_audio_path}, {translated_audio_path}")
            log_step(log_file, True, f"TEST Narrated (using cached files)")
            na_input_tokens = 0
            na_output_tokens = 0
        else:
            # Override the narrator's file path function
            original_get_file_path = narrator.get_file_path
            narrator.get_file_path = config.get_file_path
            
            summary_audio, translated_audio, na_input_tokens, na_output_tokens = narrator.narrate()
            
            # Restore original function
            narrator.get_file_path = original_get_file_path
            
            # Both audio files are now required
            if summary_audio and translated_audio:
                log_info('Test Pipeline', f"Audio files created: Summary: {summary_audio}, Translation: {translated_audio}")
                log_step(log_file, True, f"TEST Narrated using {na_input_tokens} input tokens, {na_output_tokens} output tokens for 2 audio files")
            else:
                log_error('Test Pipeline', "TTS conversion failed")
                log_step(log_file, False, "TEST Narrated")
                log_file.write("──────────\n")
                return False
        
        # Step 6: Convert to Telegraph format
        log_pipeline_step("Step 6", "Convert to Telegraph Format")
        
        # Override the telegraph_converter's file path function
        original_get_file_path = telegraph_converter.get_file_path
        telegraph_converter.get_file_path = config.get_file_path
        
        converted = telegraph_converter.convert_all_summaries()
        
        # Restore original function
        telegraph_converter.get_file_path = original_get_file_path
        
        if not converted:
            log_error('Test Pipeline', "Telegraph conversion failed")
            log_step(log_file, False, "TEST Converted to JSON")
            log_file.write("──────────\n")
            return False
        
        # Construct the converted file path since the function now returns a boolean
        converted_file = config.get_file_path('converted', date_str)
        fa_converted_file = config.get_file_path('converted', date_str, lang='FA')
        
        if os.path.exists(fa_converted_file):
            log_info('Test Pipeline', f"Content converted to Telegraph format and saved to {converted_file} and {fa_converted_file}")
        else:
            log_info('Test Pipeline', f"Content converted to Telegraph format and saved to {converted_file}")
        
        log_step(log_file, True, "TEST Converted to JSON")
        
        # Step 7: Publish to Telegraph
        log_pipeline_step("Step 7", "Publish to Telegraph")
        
        # Override the telegraph_publisher's file path function
        original_get_file_path = telegraph_publisher.get_file_path
        telegraph_publisher.get_file_path = config.get_file_path
        
        # Pass feeds_success to the publish function
        published_file = telegraph_publisher.publish(feeds_success)
        
        # Restore original function
        telegraph_publisher.get_file_path = original_get_file_path
        
        if not published_file or not os.path.exists(published_file):
            log_error('Test Pipeline', "Telegraph publishing failed")
            log_step(log_file, False, "TEST Published")
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
            log_error('Test Pipeline', f"Error reading published file: {e}")
        
        log_info('Test Pipeline', f"Content published and details saved to {published_file}")
        if telegraph_fa_url:
            log_step(log_file, True, f"TEST Published on {telegraph_url} and {telegraph_fa_url}")
        else:
            log_step(log_file, True, f"TEST Published on {telegraph_url}")
        
        # Step 8: Distribute to Telegram Channel
        log_pipeline_step("Step 8", "Distribute to Telegram Channel")
        
        # Override the telegram_distributer's file path function and config
        original_get_file_path = telegram_distributer.get_file_path
        original_chat_id = telegram_distributer.TELEGRAM_CHAT_ID
        
        telegram_distributer.get_file_path = config.get_file_path
        telegram_distributer.TELEGRAM_CHAT_ID = config.TELEGRAM_CHAT_ID
        
        telegram_url = ""
        distribution_success, telegram_url, tg_input_tokens, tg_output_tokens = telegram_distributer.distribute()
        
        # Restore original functions and config
        telegram_distributer.get_file_path = original_get_file_path
        telegram_distributer.TELEGRAM_CHAT_ID = original_chat_id
        
        if not distribution_success:
            log_error('Test Pipeline', "Telegram distribution failed")
            log_step(log_file, False, "TEST Distributed")
            log_file.write("──────────\n")
            return False
        
        log_info('Test Pipeline', "Content successfully distributed to Telegram channel")
        log_step(log_file, True, f"TEST Distributed using {tg_input_tokens} input tokens, {tg_output_tokens} output tokens at {telegram_url}")
        
        log_info('Test Pipeline', "Test pipeline completed successfully!")
        log_file.write("──────────\n")
        
        return True

if __name__ == "__main__":
    try:
        success = run_test_pipeline()
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