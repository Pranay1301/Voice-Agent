import aiohttp
from config import settings

class ElevenLabsTTSService:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = "21m00Tcm4TlvDq8ikWAM" # Default voice, can be made configurable
        self.url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"

    async def generate_speech(self, text: str):
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=data, headers=headers) as response:
                if response.status == 200:
                    async for chunk in response.content.iter_chunked(1024):
                        yield chunk
                else:
                    # Handle error
                    print(f"Error: {await response.text()}")
