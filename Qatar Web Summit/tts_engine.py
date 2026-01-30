import os
import asyncio
import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# TTS CONFIGURATION
# ============================================================================

# Chunk size for audio streaming (smaller = lower latency, but more overhead)
AUDIO_CHUNK_SIZE = 640  # ~80ms of audio at 8kHz mulaw (optimal for Twilio)

# Request timeout
TTS_TIMEOUT = 10  # seconds


class TTSEngine:
    """
    Text-to-Speech Engine using Deepgram Aura TTS.
    Optimized for low-latency voice agent use.
    
    VOICES (from most natural to least):
    - aura-athena-en (female, British - most natural)
    - aura-orion-en (male, American - professional)
    - aura-luna-en (female, American - warm)
    - aura-stella-en (female, American - soft)
    """
    
    def __init__(self):
        self.deepgram_key = os.getenv("DEEPGRAM_API_KEY")
        self.voice = os.getenv("DEEPGRAM_TTS_VOICE", "aura-athena-en")
        
        if not self.deepgram_key:
            raise Exception("DEEPGRAM_API_KEY not found")
        
        print(f"✓ TTS Engine initialized (voice: {self.voice})")
        
    async def generate_audio(self, text):
        """
        Generate audio from text in mulaw 8kHz format for Twilio.
        Yields audio chunks as they become available for low latency.
        """
        if not text or not text.strip():
            return
        
        # Clean up text for TTS
        text = self._clean_text(text)
        
        try:
            async for chunk in self._deepgram_aura_tts(text):
                yield chunk
        except Exception as e:
            print(f"⚠ Deepgram TTS error: {e}")
            # Try fallback
            try:
                async for chunk in self._gtts_fallback(text):
                    yield chunk
            except Exception as e2:
                print(f"⚠ Fallback TTS also failed: {e2}")
                # Yield silence to prevent hanging
                async for chunk in self._generate_silence(1.0):
                    yield chunk
    
    def _clean_text(self, text: str) -> str:
        """Clean text for better TTS output."""
        # Remove markdown-style formatting
        text = text.replace("**", "").replace("*", "")
        text = text.replace("✓", "").replace("✗", "")
        text = text.replace("—", " - ")  # Em dash to regular dash
        text = text.replace("…", "...")  # Ellipsis
        
        # Remove URLs (TTS shouldn't read these)
        import re
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    async def _deepgram_aura_tts(self, text):
        """Deepgram Aura TTS - Low latency, high quality streaming."""
        url = f"https://api.deepgram.com/v1/speak?model={self.voice}&encoding=mulaw&sample_rate=8000"
        
        headers = {
            "Authorization": f"Token {self.deepgram_key}",
            "Content-Type": "application/json"
        }
        
        data = {"text": text}
        
        # Use streaming request for lower latency
        response = requests.post(
            url, 
            json=data, 
            headers=headers, 
            stream=True, 
            timeout=TTS_TIMEOUT
        )
        
        if response.status_code != 200:
            error_msg = response.text[:200] if response.text else "Unknown error"
            raise Exception(f"Deepgram TTS HTTP {response.status_code}: {error_msg}")
        
        # Stream audio chunks
        chunk_count = 0
        for chunk in response.iter_content(chunk_size=AUDIO_CHUNK_SIZE):
            if chunk:
                chunk_count += 1
                yield chunk
                # Yield control to allow interrupt checking
                if chunk_count % 5 == 0:
                    await asyncio.sleep(0)
    
    async def _gtts_fallback(self, text):
        """Free Google TTS fallback (higher latency but reliable)."""
        try:
            from gtts import gTTS
            import subprocess
            import tempfile
            
            print("📢 Using gTTS fallback...")
            
            tts = gTTS(text=text, lang='en', slow=False)
            
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_mp3 = f.name
                tts.write_to_fp(f)
            
            temp_mulaw = temp_mp3.replace('.mp3', '.mulaw')
            result = subprocess.run([
                'ffmpeg', '-y', '-i', temp_mp3,
                '-af', 'atempo=1.1',  # Slightly faster
                '-ar', '8000', '-ac', '1',
                '-f', 'mulaw', temp_mulaw
            ], capture_output=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception("FFmpeg conversion failed")
            
            with open(temp_mulaw, 'rb') as f:
                mulaw_data = f.read()
            
            # Clean up temp files
            try:
                os.unlink(temp_mp3)
                os.unlink(temp_mulaw)
            except:
                pass
            
            # Yield in chunks
            for i in range(0, len(mulaw_data), AUDIO_CHUNK_SIZE):
                yield mulaw_data[i:i + AUDIO_CHUNK_SIZE]
                await asyncio.sleep(0)  # Yield control
                
        except ImportError:
            print("⚠ gTTS not installed, cannot use fallback")
            raise
        except Exception as e:
            print(f"⚠ gTTS error: {e}")
            raise
    
    async def _generate_silence(self, duration_seconds: float):
        """Generate silence audio (for error cases)."""
        # mulaw silence is 0xFF
        samples_per_chunk = AUDIO_CHUNK_SIZE
        chunks_needed = int((8000 * duration_seconds) / samples_per_chunk)
        silence_chunk = bytes([0xFF] * samples_per_chunk)
        
        for _ in range(chunks_needed):
            yield silence_chunk
            await asyncio.sleep(0)
