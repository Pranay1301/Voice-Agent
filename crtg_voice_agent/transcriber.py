import os
import json
import websockets
import asyncio
import logging
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not found")
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0

    async def _keep_alive(self):
        """Send KeepAlive messages to Deepgram every 3 seconds."""
        while self.is_connected and self.connection:
            try:
                await self.connection.send(json.dumps({"type": "KeepAlive"}))
                await asyncio.sleep(3)
            except Exception as e:
                logger.debug(f"KeepAlive failed: {e}")
                break

    async def connect(self) -> bool:
        """
        Connects to Deepgram's WebSocket API for real-time transcription.
        Returns True if connection successful, False otherwise.
        """
        if self.is_connected:
            return True
            
        url = "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000&model=nova-2&smart_format=true&interim_results=false&endpointing=1000"
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        
        try:
            # websockets 14+ uses additional_headers and open_timeout
            self.connection = await websockets.connect(url, additional_headers=headers, open_timeout=10)
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("Connected to Deepgram")
            
            # Start KeepAlive task
            asyncio.create_task(self._keep_alive())
            
            return True
        except TypeError as e:
            logger.warning(f"Connection attempt failed: {e}. Retrying with legacy arguments...")
            # Fallback for older websockets versions
            try:
                self.connection = await websockets.connect(url, extra_headers=headers)
                self.is_connected = True
                self.reconnect_attempts = 0
                logger.info("Connected to Deepgram (legacy)")
                
                # Start KeepAlive task
                asyncio.create_task(self._keep_alive())
                
                return True
            except Exception as e2:
                logger.error(f"Failed to connect to Deepgram (legacy): {e2}")
                return False
        except asyncio.TimeoutError:
            logger.error("Deepgram connection timeout")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            return False

    async def reconnect(self) -> bool:
        """Attempt to reconnect to Deepgram with exponential backoff."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return False
            
        self.reconnect_attempts += 1
        delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), 30)
        
        logger.warning(f"Attempting to reconnect to Deepgram (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}) in {delay}s")
        await asyncio.sleep(delay)
        
        return await self.connect()

    async def send_audio(self, chunk: bytes) -> bool:
        """
        Sends an audio chunk to Deepgram for transcription.
        Returns True if successful, False otherwise.
        """
        if not self.is_connected or not self.connection:
            logger.warning("Cannot send audio: not connected to Deepgram")
            return False
            
        try:
            await self.connection.send(chunk)
            return True
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Deepgram connection closed, attempting to reconnect")
            self.is_connected = False
            return await self.reconnect()
        except Exception as e:
            logger.error(f"Error sending to Deepgram: {e}")
            return False

    async def get_transcription_stream(self) -> AsyncGenerator[str, None]:
        """
        Receives streaming transcription responses from Deepgram.
        Yields partial and final transcription texts for reduced latency.
        """
        if not self.is_connected or not self.connection:
            logger.error("Cannot receive transcription: not connected to Deepgram")
            return
            
        try:
            async for message in self.connection:
                try:
                    data = json.loads(message)
                    
                    # Handle both partial and final results
                    if data.get("type") == "Results":
                        alternatives = data.get("channel", {}).get("alternatives", [])
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "").strip()
                            is_final = data.get("is_final", False)
                            
                            if transcript and len(transcript) >= 2:
                                # Yield partial results for faster response
                                if not is_final:
                                    logger.debug(f"Partial transcription: {transcript}")
                                    yield f"PARTIAL:{transcript}"
                                else:
                                    logger.debug(f"Final transcription: {transcript}")
                                    yield transcript
                                
                except json.JSONDecodeError:
                    logger.debug("Received non-JSON message from Deepgram")
                    continue
                except Exception as e:
                    logger.error(f"Error parsing Deepgram response: {e}")
                    continue
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Deepgram connection closed: {e}")
            if await self.reconnect():
                # Restart transcription after reconnection
                async for transcript in self.get_transcription_stream():
                    yield transcript
        except Exception as e:
            logger.error(f"Error receiving from Deepgram: {e}")
            if await self.reconnect():
                # Restart transcription after reconnection
                async for transcript in self.get_transcription_stream():
                    yield transcript

    async def get_transcription(self) -> AsyncGenerator[str, None]:
        """
        Receives transcription responses from Deepgram.
        Yields final transcription texts.
        """
        if not self.is_connected or not self.connection:
            logger.error("Cannot receive transcription: not connected to Deepgram")
            return
            
        try:
            async for message in self.connection:
                try:
                    data = json.loads(message)
                    
                    if data.get("type") == "Results" and data.get("is_final", False):
                        alternatives = data.get("channel", {}).get("alternatives", [])
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "").strip()
                            if transcript and len(transcript) >= 2:  # Filter out very short transcripts
                                logger.debug(f"Transcription received: {transcript}")
                                yield transcript
                                
                except json.JSONDecodeError:
                    logger.debug("Received non-JSON message from Deepgram")
                    continue
                except Exception as e:
                    logger.error(f"Error parsing Deepgram response: {e}")
                    continue
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Deepgram connection closed: {e}")
            if await self.reconnect():
                # Restart transcription after reconnection
                async for transcript in self.get_transcription():
                    yield transcript
        except Exception as e:
            logger.error(f"Error receiving from Deepgram: {e}")
            if await self.reconnect():
                # Restart transcription after reconnection
                async for transcript in self.get_transcription():
                    yield transcript

    async def close(self):
        """
        Closes the Deepgram connection.
        """
        if self.connection:
            try:
                await self.connection.close()
                self.is_connected = False
                logger.info("Deepgram connection closed")
            except Exception as e:
                logger.error(f"Error closing Deepgram connection: {e}")
        else:
            logger.warning("Deepgram connection was already closed")
