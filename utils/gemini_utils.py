#!/usr/bin/env python3
"""
Google Gemini API utilities for Sumbird pipeline.
Provides centralized clients for interacting with Gemini APIs including TTS.
"""
import os
import wave
import subprocess
from google import genai
from google.genai import types
from utils.retry_utils import with_retry_sync
from utils.logging_utils import log_error, log_info, log_success


class GeminiTextClient:
    """Client for interacting with the Gemini API for text generation."""
    
    def __init__(self, api_key, model, timeout=120):
        """Initialize the Gemini text client.
        
        Args:
            api_key (str): The Gemini API key
            model (str): The model to use for text generation
            timeout (int): Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = genai.Client(api_key=self.api_key)

    @with_retry_sync(timeout=120, max_attempts=3)
    def generate_text(self, prompt):
        """Generate text using Gemini API with retry logic.
        
        Args:
            prompt (str): The prompt to generate text from
            
        Returns:
            str: Generated text
            
        Raises:
            Exception: If text generation fails after all retries
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        
        text = response.text.strip()
        
        if not text:
            raise Exception("Generated text is empty")
        
        return text


class GeminiTTSClient:
    """Client for interacting with the Gemini TTS API."""
    
    def __init__(self, api_key, model, voice, prompt_template, timeout=120):
        """Initialize the Gemini TTS client.
        
        Args:
            api_key (str): The Gemini API key
            model (str): The TTS model to use
            voice (str): The voice to use for TTS
            prompt_template (str): The prompt template for TTS
            timeout (int): Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.prompt_template = prompt_template
        self.timeout = timeout
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
            log_error('GeminiTTS', f"Error saving WAV file {filename}", e)
            raise

    def wav_to_mp3(self, wav_file, mp3_file, title=None, artist=None, album=None, genre=None, date_str=None):
        """Convert WAV file to MP3 with metadata.
        
        Args:
            wav_file (str): Path to the WAV file
            mp3_file (str): Path to save the MP3 file
            title (str, optional): Title for the audio file metadata
            artist (str, optional): Artist for the audio file metadata
            album (str, optional): Album for the audio file metadata
            genre (str, optional): Genre for the audio file metadata
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
            if artist:
                cmd.extend(['-metadata', f'artist={artist}'])
            if album:
                cmd.extend(['-metadata', f'album={album}'])
            if genre:
                cmd.extend(['-metadata', f'genre={genre}'])
            if date_str:
                cmd.extend(['-metadata', f'date={date_str}'])
            
            cmd.append(mp3_file)
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return True
            else:
                log_error('GeminiTTS', f"FFmpeg conversion failed: {result.stderr}")
                return False
                
        except Exception as e:
            log_error('GeminiTTS', f"Error converting WAV to MP3", e)
            return False

    @with_retry_sync(timeout=120, max_attempts=3)
    def text_to_speech(self, text, output_file, title=None, artist=None, album=None, genre=None, date_str=None):
        """Convert text to speech using Gemini TTS.
        
        Args:
            text (str): Text to convert to speech
            output_file (str): Path to save the audio file
            title (str, optional): Title for the audio file metadata
            artist (str, optional): Artist for the audio file metadata
            album (str, optional): Album for the audio file metadata
            genre (str, optional): Genre for the audio file metadata
            date_str (str, optional): Date string for the audio file metadata
            
        Returns:
            str: Path to the created audio file, or None if failed
        """
        try:
            log_info('GeminiTTS', f"Converting text to speech using {self.voice} voice")
            log_info('GeminiTTS', f"Text length: {len(text)} characters")
            
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
                if self.wav_to_mp3(wav_file, output_file, title, artist, album, genre, date_str):
                    # Remove the temporary WAV file
                    os.remove(wav_file)
                    log_success('GeminiTTS', f"Audio saved as: {output_file}")
                    return output_file
                else:
                    log_info('GeminiTTS', f"Audio saved as: {wav_file} (MP3 conversion failed)")
                    return wav_file
            else:
                # Save as WAV
                self.save_wave_file(output_file, audio_data)
                log_success('GeminiTTS', f"Audio saved as: {output_file}")
                return output_file
                
        except Exception as e:
            log_error('GeminiTTS', f"Error in text_to_speech", e)
            return None


def create_gemini_text_client(api_key, model, timeout=120):
    """Factory function to create a Gemini text client.
    
    Args:
        api_key (str): The Gemini API key
        model (str): The model to use for text generation
        timeout (int): Request timeout in seconds
        
    Returns:
        GeminiTextClient: Configured client instance
    """
    return GeminiTextClient(
        api_key=api_key,
        model=model,
        timeout=timeout
    )


def create_gemini_tts_client(api_key, model, voice, prompt_template, timeout=120):
    """Factory function to create a Gemini TTS client.
    
    Args:
        api_key (str): The Gemini API key
        model (str): The TTS model to use
        voice (str): The voice to use for TTS
        prompt_template (str): The prompt template for TTS
        timeout (int): Request timeout in seconds
        
    Returns:
        GeminiTTSClient: Configured client instance
    """
    return GeminiTTSClient(
        api_key=api_key,
        model=model,
        voice=voice,
        prompt_template=prompt_template,
        timeout=timeout
    ) 