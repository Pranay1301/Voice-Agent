import os
import requests
from dotenv import load_dotenv

load_dotenv()

class TTSEngine:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Default voice (Rachel)
        
        if not self.api_key:
            raise Exception("ELEVENLABS_API_KEY not found")

    async def generate_audio(self, text):
        """
        Generates audio from text using ElevenLabs API and returns the audio content (bytes).
        """
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        # Note: For real-time streaming, we might want to use the websocket API or chunked response.
        # For simplicity in this prototype, we'll fetch the stream and return chunks.
        # But Twilio needs mulaw 8000Hz. ElevenLabs returns mp3 by default.
        # We need to request the correct format or convert it.
        # ElevenLabs supports 'output_format' parameter.
        
        # Let's update the URL to request u-law 8000Hz
        url_ulaw = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}?output_format=ulaw_8000"
        
        try:
            response = requests.post(url_ulaw, json=data, headers=headers, stream=True)
            response.raise_for_status()
            
            # Yield chunks of audio
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
                    
        except Exception as e:
            print(f"Error generating TTS: {e}")
            # Fallback or silent error handling
            pass
