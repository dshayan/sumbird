#!/usr/bin/env python3
"""
Core pipeline logic for Sumbird.

This module contains the shared pipeline execution logic that can be used
by both the main pipeline and test pipeline with different configurations.
"""
import os
import json
from utils.date_utils import get_date_str, format_datetime
from utils.logging_utils import log_step, log_pipeline_step, log_pipeline_progress, log_info, log_error, log_run_separator
from utils.file_utils import file_exists, get_audio_file_path

def run_pipeline_core(config_module, log_prefix="", test_mode=False, skip_telegram=False, force_override=False):
    """
    Core pipeline logic that works with any configuration module.
    
    Args:
        config_module: Configuration module (config or test.test_config)
        log_prefix (str): Prefix for log messages (e.g., "TEST ")
        test_mode (bool): Whether running in test mode for special handling
        skip_telegram (bool): Whether to skip the Telegram distribution step
        force_override (bool): Whether to force regeneration of all files, bypassing cache
    
    Returns:
        bool: True if pipeline completed successfully, False otherwise
    """
    # Import pipeline modules
    from src import fetcher, summarizer, translator, script_writer, narrator
    from src import telegraph_converter, telegraph_publisher, telegram_distributer
    from utils import file_utils
    
    # Ensure all directories exist before starting the pipeline
    if hasattr(config_module, 'ensure_directories'):
        config_module.ensure_directories()
    else:
        from utils.file_utils import ensure_directories
        ensure_directories()
    
    date_str = get_date_str()
    pipeline_name = f"{log_prefix}Pipeline" if log_prefix else "Pipeline"
    log_info(pipeline_name, f"Starting pipeline for date: {date_str}")
    
    # Open log file for this run
    with open(os.path.join('logs', 'log.txt'), 'a', encoding='utf-8') as log_file:
        # Log start time with consistent datetime format
        now = format_datetime()
        log_step(log_file, True, f"{log_prefix}Started at {now}")
        
        # Step 1: Fetch and format tweets
        log_pipeline_progress(1, 9, "Fetching tweets")
        
        export_file = config_module.get_file_path('export', date_str)
        using_cached_export = os.path.exists(export_file) and not force_override
        
        if using_cached_export:
            # Using cached export file
            log_info(pipeline_name, f"Using existing export file: {export_file}")
            log_step(log_file, True, f"{log_prefix}Gathered (using cached file)")
            log_step(log_file, True, f"{log_prefix}Fetched (using cached file)")
            feeds_success = 0  # We don't know the actual count from cached file
            feeds_total = 0
            failed_handles = []
        else:
            # Override the fetcher's file path function
            original_get_file_path = fetcher.get_file_path
            fetcher.get_file_path = config_module.get_file_path
            
            try:
                exported_file, feeds_success, feeds_total, failed_handles = fetcher.fetch_and_format()
            finally:
                # Restore original function
                fetcher.get_file_path = original_get_file_path
            
            if not exported_file or not os.path.exists(exported_file):
                log_error(pipeline_name, "Tweet fetching and formatting failed")
                log_step(log_file, False, f"{log_prefix}Gathered {feeds_total} sources")
                
                # Building the failed handles string
                failed_str = ""
                if failed_handles and len(failed_handles) > 0:
                    if len(failed_handles) <= 3:
                        failed_str = f" (Failed: {', '.join([fh['handle'] for fh in failed_handles])})"
                    else:
                        first_three = ', '.join([fh['handle'] for fh in failed_handles[:3]])
                        remaining = len(failed_handles) - 3
                        failed_str = f" (Failed: {first_three}, {remaining} more)"
                
                log_step(log_file, False, f"{log_prefix}Fetched {feeds_success}/{feeds_total} sources{failed_str}")
                log_run_separator()
                return False
            
            # Logging gather success (considered successful if > MIN_FEEDS_TOTAL sources)
            gather_success = feeds_total > config_module.MIN_FEEDS_TOTAL
            log_step(log_file, gather_success, f"{log_prefix}Gathered {feeds_total} sources")
            
            # Logging fetch success (considered successful if fetched/gathered >= MIN_FEEDS_SUCCESS_RATIO)
            fetch_success = (feeds_success / feeds_total >= config_module.MIN_FEEDS_SUCCESS_RATIO) if feeds_total > 0 else False
            
            # Building the failed handles string
            failed_str = ""
            if failed_handles and len(failed_handles) > 0:
                if len(failed_handles) <= 3:
                    failed_str = f" (Failed: {', '.join([fh['handle'] for fh in failed_handles])})"
                else:
                    first_three = ', '.join([fh['handle'] for fh in failed_handles[:3]])
                    remaining = len(failed_handles) - 3
                    failed_str = f" (Failed: {first_three}, {remaining} more)"
            
            log_step(log_file, fetch_success, f"{log_prefix}Fetched {feeds_success}/{feeds_total} sources{failed_str}")
        # Step 2: Summarize with AI
        log_pipeline_progress(2, 9, "Summarizing content")
        
        summary_file = config_module.get_file_path('summary', date_str)
        using_cached_summary = os.path.exists(summary_file) and not force_override
        
        if using_cached_summary:
            # Using cached summary file
            log_info(pipeline_name, f"Using existing summary file: {summary_file}")
            log_step(log_file, True, f"{log_prefix}Summarized (using cached file)")
            input_tokens = 0
            output_tokens = 0
        else:
            # Override the summarizer's file path function and title format
            original_get_file_path = summarizer.get_file_path
            original_summary_title_format = getattr(summarizer, 'SUMMARY_TITLE_FORMAT', None)
            summarizer.get_file_path = config_module.get_file_path
            if hasattr(config_module, 'SUMMARY_TITLE_FORMAT'):
                summarizer.SUMMARY_TITLE_FORMAT = config_module.SUMMARY_TITLE_FORMAT
            
            try:
                summarized_file, input_tokens, output_tokens = summarizer.summarize()
            finally:
                # Restore original functions
                summarizer.get_file_path = original_get_file_path
                if original_summary_title_format is not None:
                    summarizer.SUMMARY_TITLE_FORMAT = original_summary_title_format
            
            if not summarized_file or not os.path.exists(summarized_file):
                log_error(pipeline_name, "AI summarization failed")
                log_step(log_file, False, f"{log_prefix}Summarized")
                log_run_separator()
                return False
            
            log_step(log_file, True, f"{log_prefix}Summarized using {input_tokens} input tokens, {output_tokens} output tokens")
        
        # Step 3: Translate summary to Persian
        log_pipeline_progress(3, 9, "Translating to Persian")
        
        translated_file = config_module.get_file_path('translated', date_str)
        using_cached_translation = os.path.exists(translated_file) and not force_override
        
        if using_cached_translation:
            # Using cached translation file
            log_info(pipeline_name, f"Using existing translation file: {translated_file}")
            log_step(log_file, True, f"{log_prefix}Translated (using cached file)")
            tr_input_tokens = 0
            tr_output_tokens = 0
        else:
            # Override the translator's file path function
            original_get_file_path = translator.get_file_path
            translator.get_file_path = config_module.get_file_path
            
            try:
                translated_file, tr_input_tokens, tr_output_tokens = translator.translate()
            finally:
                # Restore original function
                translator.get_file_path = original_get_file_path
            
            # Add TEST- prefix to Persian title if in test mode
            if test_mode and translated_file and os.path.exists(translated_file):
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
                log_error(pipeline_name, "Persian translation failed")
                log_step(log_file, False, f"{log_prefix}Translated")
                log_run_separator()
                return False
            
            log_step(log_file, True, f"{log_prefix}Translated using {tr_input_tokens} input tokens, {tr_output_tokens} output tokens")
        
        # Step 4: Convert to TTS-optimized Scripts
        log_pipeline_progress(4, 9, "Creating TTS scripts")
        
        # Check if script files already exist
        summary_script_path = config_module.get_file_path('script', date_str)
        translated_script_path = config_module.get_file_path('script', date_str, lang='FA')
        using_cached_scripts = file_exists(summary_script_path) and file_exists(translated_script_path) and not force_override
        
        if using_cached_scripts:
            log_info(pipeline_name, f"Using existing script files: {summary_script_path}, {translated_script_path}")
            log_step(log_file, True, f"{log_prefix}Scripted (using cached files)")
            sc_input_tokens = 0
            sc_output_tokens = 0
        else:
            # Override the script_writer's file path function
            original_get_file_path = script_writer.get_file_path
            script_writer.get_file_path = config_module.get_file_path
            
            try:
                summary_script, translated_script, sc_input_tokens, sc_output_tokens = script_writer.write_scripts(force_override=force_override)
            finally:
                # Restore original function
                script_writer.get_file_path = original_get_file_path
            
            if not summary_script or not translated_script:
                log_error(pipeline_name, "Script writing failed")
                log_step(log_file, False, f"{log_prefix}Scripted")
                log_run_separator()
                return False
            
            log_step(log_file, True, f"{log_prefix}Scripted using {sc_input_tokens} input tokens, {sc_output_tokens} output tokens")
        
        # Step 5: Convert to Speech (TTS)
        log_pipeline_progress(5, 9, "Converting to speech")
        
        # Check if audio files already exist (check for both MP3 and WAV)
        # Override get_file_path temporarily for audio file detection
        original_utils_get_file_path = file_utils.get_file_path
        file_utils.get_file_path = config_module.get_file_path
        
        try:
            summary_audio_path = get_audio_file_path('narrated', date_str)
            translated_audio_path = get_audio_file_path('narrated', date_str, lang='FA')
            using_cached_audio = file_exists(summary_audio_path) and file_exists(translated_audio_path) and not force_override
        finally:
            # Restore original function
            file_utils.get_file_path = original_utils_get_file_path
        
        if using_cached_audio:
            log_info(pipeline_name, f"Using existing audio files: {summary_audio_path}, {translated_audio_path}")
            log_step(log_file, True, f"{log_prefix}Narrated (using cached files)")
            na_input_tokens = 0
            na_output_tokens = 0
        else:
            # Override the narrator's file path function
            original_get_file_path = narrator.get_file_path
            narrator.get_file_path = config_module.get_file_path
            
            try:
                summary_audio, translated_audio, na_input_tokens, na_output_tokens = narrator.narrate(force_override=force_override)
            finally:
                # Restore original function
                narrator.get_file_path = original_get_file_path
            
            # Both audio files are now required
            if summary_audio and translated_audio:
                log_step(log_file, True, f"{log_prefix}Narrated using {na_input_tokens} input tokens, {na_output_tokens} output tokens for 2 audio files")
            else:
                log_error(pipeline_name, "TTS conversion failed")
                log_step(log_file, False, f"{log_prefix}Narrated")
                log_run_separator()
                return False
        
        # Step 6: Convert to Telegraph format
        log_pipeline_progress(6, 9, "Converting to Telegraph format")
        
        # Override the telegraph_converter's file path function
        original_get_file_path = telegraph_converter.get_file_path
        telegraph_converter.get_file_path = config_module.get_file_path
        
        try:
            converted = telegraph_converter.convert_all_summaries()
        finally:
            # Restore original function
            telegraph_converter.get_file_path = original_get_file_path
        
        if not converted:
            log_error(pipeline_name, "Telegraph conversion failed")
            log_step(log_file, False, f"{log_prefix}Converted to JSON")
            log_run_separator()
            return False
        
        log_step(log_file, True, f"{log_prefix}Converted to JSON")
        
        # Step 7: Publish to Telegraph
        log_pipeline_progress(7, 9, "Publishing to Telegraph")
        
        # Override the telegraph_publisher's file path function
        original_get_file_path = telegraph_publisher.get_file_path
        telegraph_publisher.get_file_path = config_module.get_file_path
        
        try:
            # Pass feeds_success to the publish function
            published_file = telegraph_publisher.publish(feeds_success)
        finally:
            # Restore original function
            telegraph_publisher.get_file_path = original_get_file_path
        
        if not published_file or not os.path.exists(published_file):
            log_error(pipeline_name, "Telegraph publishing failed")
            log_step(log_file, False, f"{log_prefix}Published")
            log_run_separator()
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
            log_error(pipeline_name, f"Error reading published file: {e}")
        
        if telegraph_fa_url:
            log_step(log_file, True, f"{log_prefix}Published on {telegraph_url} and {telegraph_fa_url}")
        else:
            log_step(log_file, True, f"{log_prefix}Published on {telegraph_url}")
        
        # Step 8: Distribute to Telegram Channel (conditional)
        if skip_telegram:
            log_pipeline_progress(8, 9, "Telegram distribution (skipped)")
            log_step(log_file, True, f"{log_prefix}Distributed (skipped)")
        else:
            log_pipeline_progress(8, 9, "Distributing to Telegram")
            
            # Override the telegram_distributer's file path function and config
            # Also need to override the utils.file_utils.get_file_path that get_audio_file_path uses
            original_get_file_path = telegram_distributer.get_file_path
            original_utils_get_file_path = file_utils.get_file_path
            original_chat_id = telegram_distributer.TELEGRAM_CHAT_ID
            
            telegram_distributer.get_file_path = config_module.get_file_path
            file_utils.get_file_path = config_module.get_file_path  # This makes get_audio_file_path use correct directories
            telegram_distributer.TELEGRAM_CHAT_ID = config_module.TELEGRAM_CHAT_ID
            
            try:
                telegram_url = ""
                distribution_success, telegram_url, tg_input_tokens, tg_output_tokens = telegram_distributer.distribute()
            finally:
                # Restore original functions and config
                telegram_distributer.get_file_path = original_get_file_path
                file_utils.get_file_path = original_utils_get_file_path
                telegram_distributer.TELEGRAM_CHAT_ID = original_chat_id
            
            if not distribution_success:
                log_error(pipeline_name, "Telegram distribution failed")
                log_step(log_file, False, f"{log_prefix}Distributed")
                log_run_separator()
                return False
            
            log_step(log_file, True, f"{log_prefix}Distributed using {tg_input_tokens} input tokens, {tg_output_tokens} output tokens at {telegram_url}")
        
        # Step 9: Generate Newsletter Website (English and Farsi)
        log_pipeline_progress(9, 9, "Generating newsletters")
        
        try:
            from src import newsletter_generator
            
            newsletter_success_en = newsletter_generator.generate(language="en", verbose=False)
            newsletter_success_fa = newsletter_generator.generate(language="fa", verbose=False)
            
            newsletter_success = newsletter_success_en and newsletter_success_fa
            
        except ImportError:
            log_error(pipeline_name, "Newsletter generator not available")
            newsletter_success = False
        except Exception as e:
            log_error(pipeline_name, f"Newsletter generation failed: {e}")
            newsletter_success = False
        
        if not newsletter_success:
            log_step(log_file, False, f"{log_prefix}Newsletter generated")
            # Don't fail the entire pipeline for newsletter issues
        else:
            log_step(log_file, True, f"{log_prefix}Newsletter generated")
        log_run_separator()
        
        return True 