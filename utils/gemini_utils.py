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
    
    def __init__(self, api_key, model, timeout=None):
        """Initialize the Gemini text client.
        
        Args:
            api_key (str): The Gemini API key
            model (str): The model to use for text generation
            timeout (int): Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        # Import config here to avoid circular imports
        if timeout is None:
            from config import GEMINI_TEXT_TIMEOUT
            self.timeout = GEMINI_TEXT_TIMEOUT
        else:
            self.timeout = timeout
        self.client = genai.Client(api_key=self.api_key)

    def count_tokens(self, prompt):
        """Count tokens in a prompt using Gemini API.
        
        Args:
            prompt (str): The prompt to count tokens for
            
        Returns:
            int: Number of tokens in the prompt
            
        Raises:
            Exception: If token counting fails
        """
        try:
            response = self.client.models.count_tokens(
                model=self.model,
                contents=prompt
            )
            return response.total_tokens
        except Exception as e:
            log_error('GeminiTextClient', f"Error counting tokens", e)
            raise

    def generate_text(self, prompt):
        """Generate text using Gemini API with retry logic.
        
        Args:
            prompt (str): The prompt to generate text from
            
        Returns:
            tuple: (generated_text, input_tokens, output_tokens)
            
        Raises:
            Exception: If text generation fails after all retries
        """
        # Apply retry with instance timeout
        @with_retry_sync(timeout=self.timeout, max_attempts=3)
        def _generate_with_retry():
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            text = response.text.strip()
            
            if not text:
                raise Exception("Generated text is empty")
            
            # Extract token usage from response
            usage_metadata = response.usage_metadata
            input_tokens = usage_metadata.prompt_token_count if usage_metadata else 0
            output_tokens = usage_metadata.candidates_token_count if usage_metadata else 0
            
            return text, input_tokens, output_tokens
        
        return _generate_with_retry()


class GeminiTTSClient:
    """Client for interacting with the Gemini TTS API."""
    
    def __init__(self, api_key, model, voice, prompt_template, timeout=None):
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
        # Import config here to avoid circular imports
        if timeout is None:
            from config import TTS_TIMEOUT
            self.timeout = TTS_TIMEOUT
        else:
            self.timeout = timeout
        self.client = genai.Client(api_key=self.api_key)
        
        # Apply retry decorator with instance timeout
        self.text_to_speech = with_retry_sync(timeout=self.timeout, max_attempts=3)(self._text_to_speech_impl)

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
        """Convert WAV file to MP3 with metadata, with fallback for environments without ffmpeg.
        
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
        # Try ffmpeg first (preferred method)
        if self._try_ffmpeg_conversion(wav_file, mp3_file, title, artist, album, genre, date_str):
            return True
        
        # If ffmpeg fails, try Python-based conversion
        log_info('GeminiTTS', "FFmpeg not available, trying Python-based conversion...")
        return self._try_python_conversion(wav_file, mp3_file, title, artist, album, genre, date_str)
    
    def _try_ffmpeg_conversion(self, wav_file, mp3_file, title=None, artist=None, album=None, genre=None, date_str=None):
        """Try converting WAV to MP3 using ffmpeg.
        
        Returns:
            bool: True if successful, False if ffmpeg not available or conversion failed
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
                log_success('GeminiTTS', f"FFmpeg conversion successful: {os.path.basename(mp3_file)}")
                return True
            else:
                log_error('GeminiTTS', f"FFmpeg conversion failed: {result.stderr}")
                return False
                
        except FileNotFoundError:
            log_info('GeminiTTS', "FFmpeg not found in system PATH")
            return False
        except PermissionError:
            log_info('GeminiTTS', "FFmpeg permission denied")
            return False
        except Exception as e:
            log_error('GeminiTTS', f"FFmpeg error: {str(e)}")
            return False
    
    def _try_python_conversion(self, wav_file, mp3_file, title=None, artist=None, album=None, genre=None, date_str=None):
        """Try converting WAV to MP3 using pure Python libraries.
        
        Returns:
            bool: True if successful, False if conversion failed
        """
        try:
            # Try using lameenc for pure Python MP3 encoding
            try:
                import lameenc
                import wave
                
                log_info('GeminiTTS', f"Converting using lameenc: {os.path.basename(wav_file)} → {os.path.basename(mp3_file)}")
                
                # Read WAV file
                with wave.open(wav_file, 'rb') as wav:
                    frames = wav.readframes(wav.getnframes())
                    sample_rate = wav.getframerate()
                    channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                
                # Convert to MP3 using lameenc
                encoder = lameenc.Encoder()
                encoder.set_bit_rate(128)
                encoder.set_in_sample_rate(sample_rate)
                encoder.set_channels(channels)
                encoder.set_quality(2)  # 2 is high quality
                
                mp3_data = encoder.encode(frames)
                mp3_data += encoder.flush()
                
                # Write MP3 file
                with open(mp3_file, 'wb') as f:
                    f.write(mp3_data)
                
                # Add metadata using mutagen
                self._add_metadata_to_mp3(mp3_file, title, artist, album, genre, date_str)
                
                log_success('GeminiTTS', f"Python MP3 conversion successful: {os.path.basename(mp3_file)}")
                return True
                
            except ImportError:
                log_info('GeminiTTS', "lameenc not available, using fallback method...")
                
                # Fallback: Copy WAV file and rename to MP3 (will still be playable)
                log_info('GeminiTTS', f"No MP3 encoder available, keeping as WAV format...")
                log_info('GeminiTTS', f"Note: File will be renamed to .mp3 but remain in WAV format")
                
                import shutil
                shutil.copy2(wav_file, mp3_file)
                
                # Try to add metadata even to the copied WAV file (renamed as .mp3)
                self._add_metadata_to_mp3(mp3_file, title, artist, album, genre, date_str)
                
                log_info('GeminiTTS', f"File copied: {os.path.basename(wav_file)} → {os.path.basename(mp3_file)}")
                log_info('GeminiTTS', "Note: Audio players will still play this file correctly")
                return True
            
        except Exception as e:
            log_error('GeminiTTS', f"Python conversion error: {str(e)}")
            
            # Last resort: try simple file copy
            try:
                log_info('GeminiTTS', "Attempting simple file copy as fallback...")
                import shutil
                shutil.copy2(wav_file, mp3_file)
                
                # Try to add metadata even to the copied file
                self._add_metadata_to_mp3(mp3_file, title, artist, album, genre, date_str)
                
                log_info('GeminiTTS', f"Fallback copy successful: {os.path.basename(mp3_file)}")
                return True
            except Exception as copy_error:
                log_error('GeminiTTS', f"Fallback copy also failed: {str(copy_error)}")
                return False
    
    def _add_metadata_to_mp3(self, mp3_file, title=None, artist=None, album=None, genre=None, date_str=None):
        """Add ID3 metadata to MP3 file using mutagen.
        
        Args:
            mp3_file (str): Path to the MP3 file
            title (str, optional): Title for the audio file metadata
            artist (str, optional): Artist for the audio file metadata
            album (str, optional): Album for the audio file metadata
            genre (str, optional): Genre for the audio file metadata
            date_str (str, optional): Date string for the audio file metadata
        """
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3NoHeaderError, TIT2, TPE1, TALB, TCON, TDRC
            
            # Load the MP3 file
            try:
                audio = MP3(mp3_file)
                # Check if tags exist, if not add them
                if audio.tags is None:
                    audio.add_tags()
            except ID3NoHeaderError:
                # Add ID3 header if it doesn't exist
                audio = MP3(mp3_file)
                audio.add_tags()
            except Exception as e:
                log_error('GeminiTTS', f"Error loading MP3 file: {str(e)}")
                return
            
            # Ensure tags are available before adding metadata
            if audio.tags is None:
                log_error('GeminiTTS', "Could not initialize ID3 tags")
                return
            
            # Add metadata tags if provided
            if title:
                audio.tags.add(TIT2(encoding=3, text=title))
                log_info('GeminiTTS', f"Added title: {title}")
            
            if artist:
                audio.tags.add(TPE1(encoding=3, text=artist))
                log_info('GeminiTTS', f"Added artist: {artist}")
            
            if album:
                audio.tags.add(TALB(encoding=3, text=album))
                log_info('GeminiTTS', f"Added album: {album}")
            
            if genre:
                audio.tags.add(TCON(encoding=3, text=genre))
                log_info('GeminiTTS', f"Added genre: {genre}")
            
            if date_str:
                audio.tags.add(TDRC(encoding=3, text=date_str))
                log_info('GeminiTTS', f"Added date: {date_str}")
            
            # Save the tags
            audio.save()
            log_success('GeminiTTS', f"Metadata added to: {os.path.basename(mp3_file)}")
            
        except ImportError:
            log_info('GeminiTTS', "mutagen not available, skipping metadata addition")
        except Exception as e:
            log_error('GeminiTTS', f"Error adding metadata: {str(e)}")

    def _text_to_speech_impl(self, text, output_file, title=None, artist=None, album=None, genre=None, date_str=None):
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
            tuple: (audio_file_path, input_tokens, output_tokens) or (None, 0, 0) if failed
        """
        try:
            log_info('GeminiTTS', f"Converting text to speech using {self.voice} voice")
            log_info('GeminiTTS', f"Text length: {len(text)} characters")
            
            # Generate speech using Gemini TTS
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.prompt_template.format(text=text),
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice
                            )
                        )
                    )
                )
            )
            
            log_info('GeminiTTS', f"Response received: candidates={len(response.candidates) if response.candidates else 0}")
            
            # Enhanced error logging for response structure analysis
            try:
                # Log detailed response structure for debugging
                log_info('GeminiTTS', f"Response type: {type(response)}")
                if hasattr(response, 'candidates') and response.candidates:
                    log_info('GeminiTTS', f"First candidate type: {type(response.candidates[0])}")
                    candidate = response.candidates[0]
                    
                    # Log candidate attributes
                    if hasattr(candidate, 'content'):
                        log_info('GeminiTTS', f"Candidate content type: {type(candidate.content)}")
                        log_info('GeminiTTS', f"Candidate content is None: {candidate.content is None}")
                    else:
                        log_error('GeminiTTS', "Candidate has no 'content' attribute")
                    
                    # Log other candidate attributes for debugging
                    if hasattr(candidate, 'finish_reason'):
                        log_info('GeminiTTS', f"Candidate finish_reason: {candidate.finish_reason}")
                    if hasattr(candidate, 'safety_ratings'):
                        log_info('GeminiTTS', f"Candidate safety_ratings: {candidate.safety_ratings}")
                    if hasattr(candidate, 'citation_metadata'):
                        log_info('GeminiTTS', f"Candidate citation_metadata: {candidate.citation_metadata}")
                        
            except Exception as debug_error:
                log_error('GeminiTTS', f"Error during response structure debugging: {str(debug_error)}")
            
            # Check if response has valid candidates and content
            if not response.candidates:
                log_error('GeminiTTS', "No candidates in response")
                return None, 0, 0
            
            if not response.candidates[0].content:
                log_error('GeminiTTS', "No content in first candidate")
                # Additional debugging for empty content
                candidate = response.candidates[0]
                log_error('GeminiTTS', f"Candidate attributes: {[attr for attr in dir(candidate) if not attr.startswith('_')]}")
                if hasattr(candidate, 'finish_reason'):
                    log_error('GeminiTTS', f"Finish reason for empty content: {candidate.finish_reason}")
                return None, 0, 0
                
            if not response.candidates[0].content.parts:
                log_error('GeminiTTS', "No parts in content")
                log_error('GeminiTTS', f"Content type: {type(response.candidates[0].content)}")
                log_error('GeminiTTS', f"Content attributes: {[attr for attr in dir(response.candidates[0].content) if not attr.startswith('_')]}")
                return None, 0, 0
                
            if not response.candidates[0].content.parts[0].inline_data:
                log_error('GeminiTTS', "No inline_data in first part")
                part = response.candidates[0].content.parts[0]
                log_error('GeminiTTS', f"Part type: {type(part)}")
                log_error('GeminiTTS', f"Part attributes: {[attr for attr in dir(part) if not attr.startswith('_')]}")
                return None, 0, 0
            
            # Get the audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # Extract token usage from response
            usage_metadata = response.usage_metadata
            input_tokens = usage_metadata.prompt_token_count if usage_metadata else 0
            output_tokens = usage_metadata.candidates_token_count if usage_metadata else 0
            
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
                    return output_file, input_tokens, output_tokens
                else:
                    log_info('GeminiTTS', f"Audio saved as: {wav_file} (MP3 conversion failed)")
                    return wav_file, input_tokens, output_tokens
            else:
                # Save as WAV
                self.save_wave_file(output_file, audio_data)
                log_success('GeminiTTS', f"Audio saved as: {output_file}")
                return output_file, input_tokens, output_tokens
                
        except Exception as e:
            log_error('GeminiTTS', f"Error in text_to_speech", e)
            return None, 0, 0


def create_gemini_text_client(api_key, model, timeout=None):
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


def create_gemini_tts_client(api_key, model, voice, prompt_template, timeout=None):
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