#!/usr/bin/env python3
"""
Python-based WAV to MP3 converter for cPanel environments without ffmpeg.
Uses pydub library for audio conversion.
"""
import os
import sys
import glob
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import NARRATED_DIR, AUDIO_ARTIST, AUDIO_ALBUM, AUDIO_GENRE, TELEGRAM_AUDIO_TITLE_EN, TELEGRAM_AUDIO_TITLE_FA
from utils.logging_utils import log_info, log_success, log_error

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        from pydub import AudioSegment
        log_info('Python Converter', "pydub library found")
        return True
    except ImportError:
        log_error('Python Converter', "pydub library not found. Please install with: pip install pydub")
        return False

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

def convert_wav_to_mp3_python(wav_file, mp3_file, title=None, artist=None, album=None, genre=None, date_str=None):
    """Convert WAV to MP3 using pydub (Python-based).
    
    Args:
        wav_file (str): Path to WAV file
        mp3_file (str): Path to output MP3 file
        title (str): Audio title
        artist (str): Audio artist
        album (str): Audio album
        genre (str): Audio genre
        date_str (str): Date string
        
    Returns:
        bool: True if successful
    """
    try:
        from pydub import AudioSegment
        
        log_info('Python Converter', f"Loading WAV file: {os.path.basename(wav_file)}")
        
        # Load WAV file
        audio = AudioSegment.from_wav(wav_file)
        
        # Prepare tags for MP3
        tags = {}
        if title:
            tags['title'] = title
        if artist:
            tags['artist'] = artist
        if album:
            tags['album'] = album
        if genre:
            tags['genre'] = genre
        if date_str:
            tags['date'] = date_str
        
        log_info('Python Converter', f"Converting to MP3 with bitrate 128k...")
        
        # Export as MP3 with 128k bitrate and tags
        audio.export(
            mp3_file,
            format="mp3",
            bitrate="128k",
            tags=tags
        )
        
        return True
        
    except Exception as e:
        log_error('Python Converter', f"Error in Python conversion: {str(e)}")
        return False

def convert_wav_files():
    """Convert all WAV files in the narrated directory to MP3 using Python."""
    
    # Check dependencies first
    if not check_dependencies():
        log_error('Python Converter', "Missing dependencies. Run: pip install pydub")
        return
    
    # Ensure environment is loaded
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Find all WAV files in the narrated directory
    wav_pattern = os.path.join(NARRATED_DIR, "*.wav")
    wav_files = glob.glob(wav_pattern)
    
    if not wav_files:
        log_info('Python Converter', "No WAV files found in narrated directory")
        return
    
    log_info('Python Converter', f"Found {len(wav_files)} WAV files to convert")
    
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
                log_info('Python Converter', f"MP3 already exists, skipping: {mp3_filename}")
                continue
            
            # Extract metadata from filename
            title, date_str, is_persian = extract_metadata_from_filename(wav_filename)
            
            log_info('Python Converter', f"Converting {wav_filename} to {mp3_filename}")
            log_info('Python Converter', f"Metadata: title='{title}', date='{date_str}', persian={is_persian}")
            
            # Convert WAV to MP3 with metadata
            success = convert_wav_to_mp3_python(
                wav_file=wav_file,
                mp3_file=mp3_file,
                title=title,
                artist=AUDIO_ARTIST,
                album=AUDIO_ALBUM,
                genre=AUDIO_GENRE,
                date_str=date_str
            )
            
            if success:
                log_success('Python Converter', f"Successfully converted: {wav_filename} → {mp3_filename}")
                
                # Get file sizes for comparison
                wav_size = os.path.getsize(wav_file) / (1024 * 1024)  # MB
                mp3_size = os.path.getsize(mp3_file) / (1024 * 1024)  # MB
                compression_ratio = (1 - mp3_size / wav_size) * 100
                
                log_info('Python Converter', f"Size: {wav_size:.1f}MB → {mp3_size:.1f}MB ({compression_ratio:.1f}% smaller)")
                
                # Optionally remove the WAV file (uncomment if you want to delete originals)
                # os.remove(wav_file)
                # log_info('Python Converter', f"Removed original WAV file: {wav_filename}")
                
                converted_count += 1
            else:
                log_error('Python Converter', f"Failed to convert: {wav_filename}")
                failed_count += 1
                
        except Exception as e:
            log_error('Python Converter', f"Error processing {wav_file}", e)
            failed_count += 1
    
    # Summary
    log_info('Python Converter', f"Conversion complete: {converted_count} successful, {failed_count} failed")
    
    if converted_count > 0:
        log_success('Python Converter', f"Successfully converted {converted_count} WAV files to MP3")
    
    if failed_count > 0:
        log_error('Python Converter', f"{failed_count} conversions failed")

if __name__ == "__main__":
    convert_wav_files() 