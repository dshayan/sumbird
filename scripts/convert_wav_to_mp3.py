#!/usr/bin/env python3
"""
Script to convert existing WAV files in /data/narrated to MP3 format.
Uses the existing converter from gemini_utils.py with proper metadata.
"""
import os
import glob
from pathlib import Path

# Add the project root to Python path so we can import modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NARRATED_DIR, AUDIO_ARTIST, AUDIO_ALBUM, AUDIO_GENRE, TELEGRAM_AUDIO_TITLE_EN, TELEGRAM_AUDIO_TITLE_FA
from utils.gemini_utils import GeminiTTSClient
from utils.logging_utils import log_info, log_success, log_error


def extract_metadata_from_filename(wav_filename):
    """Extract metadata from filename for proper MP3 tagging.
    
    Args:
        wav_filename (str): WAV filename (e.g., 'X-2025-06-30.wav' or 'X-2025-06-30-FA.wav')
        
    Returns:
        tuple: (title, date_str, is_persian)
    """
    # Remove .wav extension
    base_name = wav_filename.replace('.wav', '')
    
    # Check if it's Persian (ends with -FA)
    is_persian = base_name.endswith('-FA')
    if is_persian:
        base_name = base_name[:-3]  # Remove -FA suffix
    
    # Extract date (format: X-YYYY-MM-DD)
    parts = base_name.split('-')
    if len(parts) >= 4:
        date_str = f"{parts[1]}-{parts[2]}-{parts[3]}"
    else:
        date_str = "Unknown"
    
    # Set title based on language
    title = TELEGRAM_AUDIO_TITLE_FA if is_persian else TELEGRAM_AUDIO_TITLE_EN
    
    return title, date_str, is_persian


def convert_wav_files():
    """Convert all WAV files in the narrated directory to MP3."""
    
    # Ensure environment is loaded
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Find all WAV files in the narrated directory
    wav_pattern = os.path.join(NARRATED_DIR, "*.wav")
    wav_files = glob.glob(wav_pattern)
    
    if not wav_files:
        log_info('WAV Converter', "No WAV files found in narrated directory")
        return
    
    log_info('WAV Converter', f"Found {len(wav_files)} WAV files to convert")
    
    # Create a dummy TTS client just to use its wav_to_mp3 method
    # We don't need the actual TTS functionality, just the converter
    dummy_client = GeminiTTSClient(
        api_key="dummy",  # Not used for conversion
        model="dummy",    # Not used for conversion
        voice="dummy",    # Not used for conversion
        prompt_template="dummy"  # Not used for conversion
    )
    
    converted_count = 0
    failed_count = 0
    
    for wav_file in wav_files:
        try:
            # Extract filename and create MP3 path
            wav_filename = os.path.basename(wav_file)
            mp3_filename = wav_filename.replace('.wav', '.mp3')
            mp3_file = os.path.join(NARRATED_DIR, mp3_filename)
            
            # Check if MP3 already exists
            if os.path.exists(mp3_file):
                log_info('WAV Converter', f"MP3 already exists, skipping: {mp3_filename}")
                continue
            
            # Extract metadata from filename
            title, date_str, is_persian = extract_metadata_from_filename(wav_filename)
            
            log_info('WAV Converter', f"Converting {wav_filename} to {mp3_filename}")
            log_info('WAV Converter', f"Metadata: title='{title}', date='{date_str}', persian={is_persian}")
            
            # Convert WAV to MP3 with metadata
            success = dummy_client.wav_to_mp3(
                wav_file=wav_file,
                mp3_file=mp3_file,
                title=title,
                artist=AUDIO_ARTIST,
                album=AUDIO_ALBUM,
                genre=AUDIO_GENRE,
                date_str=date_str
            )
            
            if success:
                log_success('WAV Converter', f"Successfully converted: {wav_filename} → {mp3_filename}")
                
                # Get file sizes for comparison
                wav_size = os.path.getsize(wav_file) / (1024 * 1024)  # MB
                mp3_size = os.path.getsize(mp3_file) / (1024 * 1024)  # MB
                compression_ratio = (1 - mp3_size / wav_size) * 100
                
                log_info('WAV Converter', f"Size: {wav_size:.1f}MB → {mp3_size:.1f}MB ({compression_ratio:.1f}% smaller)")
                
                # Optionally remove the WAV file (uncomment if you want to delete originals)
                # os.remove(wav_file)
                # log_info('WAV Converter', f"Removed original WAV file: {wav_filename}")
                
                converted_count += 1
            else:
                log_error('WAV Converter', f"Failed to convert: {wav_filename}")
                failed_count += 1
                
        except Exception as e:
            log_error('WAV Converter', f"Error processing {wav_file}", e)
            failed_count += 1
    
    # Summary
    log_info('WAV Converter', f"Conversion complete: {converted_count} successful, {failed_count} failed")
    
    if converted_count > 0:
        log_success('WAV Converter', f"Successfully converted {converted_count} WAV files to MP3")
    
    if failed_count > 0:
        log_error('WAV Converter', f"{failed_count} conversions failed")


if __name__ == "__main__":
    convert_wav_files() 