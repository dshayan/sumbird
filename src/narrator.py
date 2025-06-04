#!/usr/bin/env python3
"""
Module for converting text content to speech using Gemini 2.5 Flash TTS.
This module can be run independently or as part of the pipeline.
"""
import os
import wave
import time
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE, NARRATOR_PROMPT_PATH,
    SCRIPT_DIR, NARRATED_DIR, AUDIO_ARTIST, AUDIO_ALBUM, AUDIO_GENRE,
    TELEGRAM_AUDIO_TITLE_EN, TELEGRAM_AUDIO_TITLE_FA,
    get_date_str, get_file_path, AI_TIMEOUT, RETRY_MAX_ATTEMPTS
)
from utils.logging_utils import log_error, log_info, log_success
from utils.html_utils import html_to_text
from utils.file_utils import file_exists, read_file
from utils.retry_utils import with_retry_sync

class NarratorClient:
    """Client for interacting with the Gemini TTS API."""
    
    def __init__(self, api_key, model, voice, prompt_template):
        """Initialize the Gemini TTS client.
        
        Args:
            api_key (str): The Gemini API key
            model (str): The TTS model to use
            voice (str): The voice to use for TTS
            prompt_template (str): The prompt template for TTS
        """
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.prompt_template = prompt_template
        self.client = genai.Client(api_key=self.api_key)

    def save_wave_file(self, filename, pcm_data):
        """Save PCM data as a WAV file.
        
        Args:
            filename (str): Path to save the WAV file
            pcm_data (bytes): PCM audio data
        """
        try:
            with wave.open(filename, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(pcm_data)
        except Exception as e:
            log_error('Narrator', f"Error saving WAV file {filename}", e)
            raise

    def wav_to_mp3(self, wav_file, mp3_file, title=None, date_str=None):
        """Convert WAV file to MP3 with metadata.
        
        Args:
            wav_file (str): Path to the WAV file
            mp3_file (str): Path to save the MP3 file
            title (str, optional): Title for the audio file metadata
            date_str (str, optional): Date string for the audio file metadata
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            # Build ffmpeg command
            cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-i', wav_file,
                '-codec:a', 'libmp3lame',
                '-b:a', '128k'
            ]
            
            # Add metadata if provided
            if title:
                cmd.extend(['-metadata', f'title={title}'])
            if AUDIO_ARTIST:
                cmd.extend(['-metadata', f'artist={AUDIO_ARTIST}'])
            if AUDIO_ALBUM:
                cmd.extend(['-metadata', f'album={AUDIO_ALBUM}'])
            if AUDIO_GENRE:
                cmd.extend(['-metadata', f'genre={AUDIO_GENRE}'])
            if date_str:
                cmd.extend(['-metadata', f'date={date_str}'])
            
            cmd.append(mp3_file)
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True
            else:
                log_error('Narrator', f"FFmpeg conversion failed: {result.stderr}")
                return False
                
        except Exception as e:
            log_error('Narrator', f"Error converting WAV to MP3", e)
            return False

    @with_retry_sync(timeout=AI_TIMEOUT, max_attempts=RETRY_MAX_ATTEMPTS)
    def text_to_speech(self, text, output_file, title=None, date_str=None):
        """Convert text to speech using Gemini TTS.
        
        Args:
            text (str): Text to convert to speech
            output_file (str): Path to save the audio file
            title (str, optional): Title for the audio file metadata
            date_str (str, optional): Date string for the audio file metadata
            
        Returns:
            str: Path to the created audio file, or None if failed
        """
        try:
            log_info('Narrator', f"Converting text to speech using {self.voice} voice")
            log_info('Narrator', f"Text length: {len(text)} characters")
            
            # Generate speech using Gemini TTS
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.prompt_template.format(text=text),
                config=types.GenerateContentConfig(
                    system_instruction="You are a professional narrator. Convert the provided text to natural, engaging speech.",
                    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(name=self.voice))
                )
            )
            
            # Get the audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # Determine output format and save accordingly
            if output_file.endswith('.mp3'):
                # Save as WAV first, then convert to MP3
                wav_file = output_file.replace('.mp3', '.wav')
                self.save_wave_file(wav_file, audio_data)
                
                # Convert to MP3
                if self.wav_to_mp3(wav_file, output_file, title, date_str):
                    # Remove the temporary WAV file
                    os.remove(wav_file)
                    log_success('Narrator', f"Audio saved as: {output_file}")
                    return output_file
                else:
                    log_info('Narrator', f"Audio saved as: {wav_file} (MP3 conversion failed)")
                    return wav_file
            else:
                # Save as WAV
                self.save_wave_file(output_file, audio_data)
                log_success('Narrator', f"Audio saved as: {output_file}")
                return output_file
                
        except Exception as e:
            log_error('Narrator', f"Error in text_to_speech", e)
            return None

def convert_html_to_text(html_content):
    """Convert HTML content to clean text for TTS.
    
    Args:
        html_content (str): HTML content to convert
        
    Returns:
        str: Clean text suitable for TTS
    """
    # Use the existing html_to_text utility
    text_content = html_to_text(html_content)
    
    # Additional cleaning for TTS
    # Remove markdown-style headers
    text_content = text_content.replace('# ', '').replace('## ', '').replace('### ', '')
    
    # Clean up any remaining formatting
    text_content = ' '.join(text_content.split())
    
    return text_content

def narrate_file(file_path, output_path, client, title=None, date_str=None):
    """Convert a single file to speech.
    
    Args:
        file_path (str): Path to the input file
        output_path (str): Path to save the audio file
        client (NarratorClient): TTS client instance
        title (str, optional): Title for the audio file metadata
        date_str (str, optional): Date string for the audio file metadata
        
    Returns:
        str: Path to the created audio file, or None if failed
    """
    try:
        if not file_exists(file_path):
            log_error('Narrator', f"Input file not found: {file_path}")
            return None
        
        # Read the file content
        html_content = read_file(file_path)
        
        # Convert HTML to text
        text_content = convert_html_to_text(html_content)
        
        if not text_content.strip():
            log_error('Narrator', f"No text content found in {file_path}")
            return None
        
        log_info('Narrator', f"Processing {file_path}")
        log_info('Narrator', f"Text preview: {text_content[:200]}...")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convert to speech
        return client.text_to_speech(text_content, output_path, title, date_str)
        
    except Exception as e:
        log_error('Narrator', f"Error processing file {file_path}", e)
        return None

def narrate():
    """Main function to convert summary and translated files to speech.
    
    Returns:
        tuple: (summary_audio_path, translated_audio_path) where paths are strings or None if failed
    """
    try:
        # Get the target date
        date_str = get_date_str()
        
        # Read the narrator prompt
        with open(NARRATOR_PROMPT_PATH, 'r', encoding='utf-8') as f:
            prompt_template = f.read().strip()
        
        # Get file paths
        script_file = get_file_path('script', date_str)
        translated_script_file = get_file_path('script', date_str, lang='FA')
        
        # Verify both required files exist
        if not file_exists(script_file):
            log_error('Narrator', f"Required script file not found: {script_file}")
            return None, None
        
        if not file_exists(translated_script_file):
            log_error('Narrator', f"Required translated script file not found: {translated_script_file}")
            return None, None
        
        # Generate output paths
        summary_audio = get_file_path('narrated', date_str)
        translated_audio = get_file_path('narrated', date_str, lang='FA')
        
        summary_result = None
        translated_result = None
        
        # Check if summary audio already exists
        if file_exists(summary_audio):
            log_info('Narrator', f"Using existing summary audio: {summary_audio}")
            summary_result = summary_audio
        else:
            log_info('Narrator', "Converting Script to Speech")
            client = NarratorClient(
                api_key=GEMINI_API_KEY,
                model=GEMINI_TTS_MODEL,
                voice=GEMINI_TTS_VOICE,
                prompt_template=prompt_template
            )
            summary_result = narrate_file(script_file, summary_audio, client, TELEGRAM_AUDIO_TITLE_EN, date_str)
            if summary_result:
                log_success('Narrator', f"Script audio created: {summary_result}")
            else:
                log_error('Narrator', "Failed to create required script audio")
                return None, None
        
        # Wait between requests to avoid rate limiting
        if not file_exists(translated_audio):
            log_info('Narrator', "Waiting 1 minute before converting Persian script...")
            time.sleep(60)
        
        # Check if translated audio already exists
        if file_exists(translated_audio):
            log_info('Narrator', f"Using existing translation audio: {translated_audio}")
            translated_result = translated_audio
        else:
            log_info('Narrator', "Converting Translation Script to Speech")
            # Initialize TTS client if not already initialized
            if 'client' not in locals():
                client = NarratorClient(
                    api_key=GEMINI_API_KEY,
                    model=GEMINI_TTS_MODEL,
                    voice=GEMINI_TTS_VOICE,
                    prompt_template=prompt_template
                )
            translated_result = narrate_file(translated_script_file, translated_audio, client, TELEGRAM_AUDIO_TITLE_FA, date_str)
            if translated_result:
                log_success('Narrator', f"Translation script audio created: {translated_result}")
            else:
                log_error('Narrator', "Failed to create required translation script audio")
                return None, None
        
        return summary_result, translated_result
        
    except Exception as e:
        log_error('Narrator', f"Error in narrate function", e)
        return None, None

if __name__ == "__main__":
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(NARRATED_DIR):
        log_info('Narrator', f"Creating directory: {NARRATED_DIR}")
        os.makedirs(NARRATED_DIR, exist_ok=True)
    
    summary_audio, translated_audio = narrate()
    
    if summary_audio and translated_audio:
        log_success('Narrator', "Narration completed successfully")
        log_info('Narrator', f"Summary audio: {summary_audio}")
        log_info('Narrator', f"Translation audio: {translated_audio}")
    else:
        log_error('Narrator', "Narration failed") 