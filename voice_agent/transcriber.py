import os
import json
import asyncio
import websockets
from dotenv import load_dotenv

load_dotenv()

class Transcriber:
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise Exception("DEEPGRAM_API_KEY not found")
        self.connection = None

    async def connect(self):
        """
        Connects to Deepgram's WebSocket API for real-time transcription.
        """
        # Using the Deepgram WebSocket API directly for better control over the stream
        # Model: nova-2 is generally good for general purpose, but let's stick to a fast one.
        url = "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&model=nova-2&smart_format=true"
        extra_headers = {
            "Authorization": f"Token {self.api_key}"
        }
        
        try:
            self.connection = await websockets.connect(url, extra_headers=extra_headers)
            print("Connected to Deepgram")
            return self.connection
        except Exception as e:
            print(f"Failed to connect to Deepgram: {e}")
            raise e

    async def send_audio(self, chunk):
        """
        Sends audio chunk to Deepgram.
        """
        if self.connection:
            await self.connection.send(chunk)

    async def get_transcription(self):
        """
        Yields transcriptions from Deepgram.
        """
        if not self.connection:
            raise Exception("Not connected to Deepgram")

        try:
            async for message in self.connection:
                data = json.loads(message)
                if "channel" in data:
                    alternatives = data["channel"]["alternatives"]
                    if alternatives:
                        transcript = alternatives[0]["transcript"]
                        if transcript and data["is_final"]:
                            yield transcript
        except websockets.exceptions.ConnectionClosed:
            print("Deepgram connection closed")
        except Exception as e:
            print(f"Error receiving from Deepgram: {e}")

    async def close(self):
        if self.connection:
            await self.connection.close()
