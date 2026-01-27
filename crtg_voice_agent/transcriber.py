import os
import json
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
        url = "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&model=nova-2&smart_format=true&interim_results=false"
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        
        try:
            self.connection = await websockets.connect(url, additional_headers=headers)
            print("Connected to Deepgram")
            return self.connection
        except TypeError:
            # Fallback for older websockets versions
            self.connection = await websockets.connect(url, extra_headers=headers)
            print("Connected to Deepgram (legacy)")
            return self.connection
        except Exception as e:
            print(f"Failed to connect to Deepgram: {e}")
            raise e

    async def send_audio(self, chunk):
        """
        Sends an audio chunk to Deepgram for transcription.
        """
        if self.connection:
            try:
                await self.connection.send(chunk)
            except Exception as e:
                print(f"Error sending to Deepgram: {e}")

    async def get_transcription(self):
        """
        Receives transcription responses from Deepgram.
        Yields final transcription texts.
        """
        if not self.connection:
            return
            
        try:
            async for message in self.connection:
                try:
                    data = json.loads(message)
                    
                    # Deepgram response structure:
                    # {"type": "Results", "channel_index": [0,1], "is_final": true, 
                    #  "channel": {"alternatives": [{"transcript": "hello", ...}]}}
                    
                    if data.get("type") == "Results" and data.get("is_final", False):
                        alternatives = data.get("channel", {}).get("alternatives", [])
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "").strip()
                            if transcript:
                                yield transcript
                                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error parsing Deepgram response: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("Deepgram connection closed")
        except Exception as e:
            print(f"Error receiving from Deepgram: {e}")

    async def close(self):
        """
        Closes the Deepgram connection.
        """
        if self.connection:
            try:
                await self.connection.close()
                print("Deepgram connection closed")
            except Exception as e:
                print(f"Error closing Deepgram connection: {e}")
