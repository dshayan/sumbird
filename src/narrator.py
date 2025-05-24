#!/usr/bin/env python3
"""
Module for converting text content to speech using Gemini 2.5 Flash TTS.
This module can be run independently or as part of the pipeline.
"""
import os
import wave
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY, GEMINI_TTS_MODEL, GEMINI_TTS_VOICE, NARRATOR_PROMPT_PATH,
    SUMMARY_DIR, TRANSLATED_DIR, NARRATED_DIR,
    get_date_str, get_file_path
)
from utils.logging_utils import log_error
from utils.html_utils import html_to_text
from utils.file_utils import file_exists, read_file

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

    def wav_to_mp3(self, wav_file, mp3_file):
        """Convert WAV to MP3 using ffmpeg.
        
        Args:
            wav_file (str): Path to the WAV file
            mp3_file (str): Path to save the MP3 file
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            subprocess.run([
                'ffmpeg', '-i', wav_file, '-codec:a', 'libmp3lame', 
                '-b:a', '128k', mp3_file, '-y'
            ], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            log_error('Narrator', f"ffmpeg conversion failed for {wav_file}", e)
            return False
        except FileNotFoundError:
            log_error('Narrator', "ffmpeg not found. Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Ubuntu)")
            return False

    def text_to_speech(self, text, output_file):
        """Convert text to speech using Gemini TTS.
        
        Args:
            text (str): Text content to convert
            output_file (str): Path to save the audio file
            
        Returns:
            str: Path to the created audio file, or None if failed
        """
        try:
            print(f"Converting text to speech using {self.voice} voice")
            print(f"Text length: {len(text)} characters")
            
            # Create TTS request
            prompt = self.prompt_template.format(text=text)
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice,
                            )
                        )
                    ),
                )
            )
            
            # Extract audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # Save as WAV first
            wav_file = output_file.replace('.mp3', '.wav')
            self.save_wave_file(wav_file, audio_data)
            
            # Convert to MP3
            if output_file.endswith('.mp3'):
                if self.wav_to_mp3(wav_file, output_file):
                    os.remove(wav_file)  # Remove WAV file after successful conversion
                    print(f"Audio saved as: {output_file}")
                    return output_file
                else:
                    print(f"Audio saved as: {wav_file} (MP3 conversion failed)")
                    return wav_file
            else:
                print(f"Audio saved as: {wav_file}")
                return wav_file
                
        except Exception as e:
            log_error('Narrator', f"Error converting text to speech", e)
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

def narrate_file(file_path, output_path, client):
    """Convert a single file to speech.
    
    Args:
        file_path (str): Path to the input file
        output_path (str): Path to save the audio file
        client (NarratorClient): TTS client instance
        
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
        
        print(f"Processing {file_path}")
        print(f"Text preview: {text_content[:200]}...")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convert to speech
        return client.text_to_speech(text_content, output_path)
        
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
        summary_file = get_file_path('summary', date_str)
        translated_file = get_file_path('translated', date_str)
        
        # Verify both required files exist
        if not file_exists(summary_file):
            log_error('Narrator', f"Required summary file not found: {summary_file}")
            return None, None
        
        if not file_exists(translated_file):
            log_error('Narrator', f"Required translated file not found: {translated_file}")
            return None, None
        
        # Generate output paths
        summary_audio = get_file_path('narrated', date_str)
        translated_audio = get_file_path('narrated', date_str, lang='FA')
        
        summary_result = None
        translated_result = None
        
        # Check if summary audio already exists
        if file_exists(summary_audio):
            print(f"Using existing summary audio: {summary_audio}")
            summary_result = summary_audio
        else:
            print(f"\n=== Converting Summary to Speech ===")
            # Initialize TTS client
            client = NarratorClient(
                api_key=GEMINI_API_KEY,
                model=GEMINI_TTS_MODEL,
                voice=GEMINI_TTS_VOICE,
                prompt_template=prompt_template
            )
            summary_result = narrate_file(summary_file, summary_audio, client)
            if summary_result:
                print(f"Summary audio created: {summary_result}")
            else:
                log_error('Narrator', "Failed to create required summary audio")
                return None, None
        
        # Check if translated audio already exists
        if file_exists(translated_audio):
            print(f"Using existing translation audio: {translated_audio}")
            translated_result = translated_audio
        else:
            print(f"\n=== Converting Translation to Speech ===")
            # Initialize TTS client if not already initialized
            if 'client' not in locals():
                client = NarratorClient(
                    api_key=GEMINI_API_KEY,
                    model=GEMINI_TTS_MODEL,
                    voice=GEMINI_TTS_VOICE,
                    prompt_template=prompt_template
                )
            translated_result = narrate_file(translated_file, translated_audio, client)
            if translated_result:
                print(f"Translation audio created: {translated_result}")
            else:
                log_error('Narrator', "Failed to create required translation audio")
                return None, None
        
        return summary_result, translated_result
        
    except Exception as e:
        log_error('Narrator', f"Error in narrate function", e)
        return None, None

if __name__ == "__main__":
    # Create necessary directories when running as standalone
    if not os.path.exists(NARRATED_DIR):
        print(f"Creating directory: {NARRATED_DIR}")
        os.makedirs(NARRATED_DIR, exist_ok=True)
    
    summary_audio, translated_audio = narrate()
    
    if summary_audio or translated_audio:
        print(f"\nNarration completed successfully")
        if summary_audio:
            print(f"Summary audio: {summary_audio}")
        if translated_audio:
            print(f"Translation audio: {translated_audio}")
    else:
        print("\nNarration failed") 