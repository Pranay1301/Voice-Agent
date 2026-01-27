import os
import tempfile
import requests
from dotenv import load_dotenv

load_dotenv()

class TTSEngine:
    def __init__(self):
        self.elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.use_elevenlabs = bool(self.elevenlabs_key)
        
    async def generate_audio(self, text):
        """Generate audio from text in mulaw 8kHz format for Twilio."""
        if not text or not text.strip():
            return
            
        # Try ElevenLabs first
        if self.use_elevenlabs:
            try:
                async for chunk in self._elevenlabs_tts(text):
                    yield chunk
                return
            except Exception as e:
                print(f"ElevenLabs failed: {e}, trying gTTS...")
                self.use_elevenlabs = False
        
        # Fallback to gTTS
        async for chunk in self._gtts_fallback(text):
            yield chunk
    
    async def _elevenlabs_tts(self, text):
        """ElevenLabs Flash TTS with mulaw output for Twilio - optimized for low latency."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream?output_format=ulaw_8000"
        
        headers = {
            "Accept": "audio/basic",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_flash_v2_5",  # Flash model for low latency
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "speed": 1.0
            }
        }

        response = requests.post(url, json=data, headers=headers, stream=True, timeout=15)
        
        if response.status_code == 401:
            raise Exception("ElevenLabs 401 Unauthorized - check API key permissions")
        
        response.raise_for_status()
        
        # Stream audio chunks as they arrive
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk
    
    async def _gtts_fallback(self, text):
        """Free Google TTS fallback - uses ffmpeg for faster, better quality mulaw conversion."""
        try:
            from gtts import gTTS
            import subprocess
            
            # Generate MP3 with gTTS (fast mode)
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_mp3 = f.name
                tts.write_to_fp(f)
            
            # Convert MP3 to mulaw 8kHz using ffmpeg with speed boost
            temp_mulaw = temp_mp3.replace('.mp3', '.mulaw')
            result = subprocess.run([
                'ffmpeg', '-y', '-i', temp_mp3,
                '-af', 'atempo=1.2,highpass=f=200,lowpass=f=3000',
                '-ar', '8000', '-ac', '1',
                '-f', 'mulaw', temp_mulaw
            ], capture_output=True, timeout=30)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr.decode()}")
                raise Exception("FFmpeg conversion failed")
            
            # Read the mulaw file and yield chunks
            with open(temp_mulaw, 'rb') as f:
                mulaw_data = f.read()
            
            # Clean up temp files
            os.unlink(temp_mp3)
            os.unlink(temp_mulaw)
            
            # Yield in chunks
            chunk_size = 1024
            for i in range(0, len(mulaw_data), chunk_size):
                yield mulaw_data[i:i + chunk_size]
                
            print(f"gTTS generated audio for: {text[:50]}...")
            
        except ImportError:
            print("gTTS not installed, yielding silence")
            silence = bytes([0xFF] * 160)
            for _ in range(20):
                yield silence
        except Exception as e:
            print(f"gTTS error: {e}")
            silence = bytes([0xFF] * 160)
            for _ in range(20):
                yield silence
