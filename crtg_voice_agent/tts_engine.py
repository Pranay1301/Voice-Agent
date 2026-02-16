import os
import requests
import asyncio
import logging
from typing import AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class TTSEngine:
    """
    Text-to-Speech Engine using Deepgram Aura TTS.
    
    VOICES (from most natural to least):
    - aura-athena-en (female, British - most natural)
    - aura-orion-en (male, American - professional)
    - aura-arcas-en (male, deep)
    - aura-stella-en (female, warm)
    """
    
    def __init__(self):
        self.deepgram_key = os.getenv("DEEPGRAM_API_KEY")
        # Using Athena - British female, most natural sounding
        self.voice = os.getenv("DEEPGRAM_TTS_VOICE", "aura-athena-en")
        self.max_retries = 3
        self.timeout = 15
        
        if not self.deepgram_key:
            raise ValueError("DEEPGRAM_API_KEY not found")
        
    async def generate_audio_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """Generate audio from text with streaming support for reduced latency."""
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS engine")
            return
        
        # Clean and validate text
        text = self._clean_text(text)
        if len(text) < 2:
            logger.warning("Text too short for TTS")
            return
        
        # Try Deepgram first with retry logic
        for attempt in range(self.max_retries):
            try:
                async for chunk in self._deepgram_aura_tts_stream(text):
                    yield chunk
                return  # Success
            except Exception as e:
                logger.error(f"Deepgram TTS attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.warning("All Deepgram attempts failed, falling back to gTTS...")
                    async for chunk in self._gtts_fallback(text):
                        yield chunk
                else:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

    async def generate_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        """Generate audio from text in mulaw 8kHz format for Twilio."""
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS engine")
            return
        
        # Clean and validate text
        text = self._clean_text(text)
        if len(text) < 2:
            logger.warning("Text too short for TTS")
            return
        
        # Try Deepgram first with retry logic
        for attempt in range(self.max_retries):
            try:
                async for chunk in self._deepgram_aura_tts(text):
                    yield chunk
                return  # Success
            except Exception as e:
                logger.error(f"Deepgram TTS attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.warning("All Deepgram attempts failed, falling back to gTTS...")
                    async for chunk in self._gtts_fallback(text):
                        yield chunk
                else:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
    
    def _clean_text(self, text: str) -> str:
        """Clean and validate text for TTS."""
        # Remove excessive whitespace and newlines
        text = ' '.join(text.split())
        
        # Limit text length to prevent API issues
        if len(text) > 500:
            text = text[:500] + "..."
        
        # Remove any problematic characters
        text = text.replace('*', '').replace('_', '').replace('#', '')
        
        return text.strip()
    
    async def _deepgram_aura_tts(self, text: str) -> AsyncGenerator[bytes, None]:
        """Deepgram Aura TTS - Low latency, high quality."""
        url = f"https://api.deepgram.com/v1/speak?model={self.voice}&encoding=mulaw&sample_rate=8000"
        
        headers = {
            "Authorization": f"Token {self.deepgram_key}",
            "Content-Type": "application/json"
        }
        
        data = {"text": text}
        
        try:
            response = requests.post(url, json=data, headers=headers, stream=True, timeout=self.timeout)
            
            if response.status_code != 200:
                error_msg = response.text[:200] if response.text else "Unknown error"
                raise Exception(f"Deepgram TTS HTTP {response.status_code}: {error_msg}")
            
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
                    
            logger.info(f"Deepgram TTS generated audio for: {text[:50]}...")
            
        except requests.exceptions.Timeout:
            raise Exception("Deepgram TTS request timed out")
        except requests.exceptions.ConnectionError:
            raise Exception("Deepgram TTS connection error")
        except Exception as e:
            logger.error(f"Deepgram TTS error: {e}")
            raise e
    
    async def _gtts_fallback(self, text: str) -> AsyncGenerator[bytes, None]:
        """Free Google TTS fallback with improved error handling."""
        try:
            from gtts import gTTS
            import subprocess
            import tempfile
            import os
            
            logger.info("Using gTTS fallback for text generation")
            
            tts = gTTS(text=text, lang='en', slow=False)
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_mp3 = f.name
                tts.write_to_fp(f)
            
            temp_mulaw = temp_mp3.replace('.mp3', '.mulaw')
            
            try:
                result = subprocess.run([
                    'ffmpeg', '-y', '-i', temp_mp3,
                    '-af', 'atempo=1.1',
                    '-ar', '8000', '-ac', '1',
                    '-f', 'mulaw', temp_mulaw
                ], capture_output=True, timeout=30)
                
                if result.returncode != 0:
                    error_msg = result.stderr.decode()[:200]
                    raise Exception(f"FFmpeg conversion failed: {error_msg}")
                
                with open(temp_mulaw, 'rb') as f:
                    mulaw_data = f.read()
                
                # Clean up temporary files
                os.unlink(temp_mp3)
                os.unlink(temp_mulaw)
                
                # Stream the audio data
                for i in range(0, len(mulaw_data), 1024):
                    yield mulaw_data[i:i + 1024]
                    
                logger.info(f"gTTS fallback generated audio for: {text[:50]}...")
                
            except subprocess.TimeoutExpired:
                raise Exception("FFmpeg conversion timed out")
            except Exception as e:
                logger.error(f"FFmpeg conversion error: {e}")
                raise e
                
        except ImportError:
            logger.error("gTTS not available, generating silence")
            async for chunk in self._generate_silence():
                yield chunk
        except Exception as e:
            logger.error(f"gTTS fallback error: {e}")
            async for chunk in self._generate_silence():
                yield chunk
    
    async def _generate_silence(self) -> AsyncGenerator[bytes, None]:
        """Generate silence as last resort."""
        logger.warning("Generating silence due to TTS failure")
        silence = bytes([0xFF] * 160)  # 20ms of silence at 8kHz
        for _ in range(20):  # 400ms of silence
            yield silence
            await asyncio.sleep(0.02)  # 20ms delay
