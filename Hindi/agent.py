from services.asr_reverie import ReverieASRService
from services.stt_google import GoogleSTTService
from services.tts_elevenlabs import ElevenLabsTTSService
from services.llm import LLMService

class VoiceAgent:
    def __init__(self):
        self.asr_service = ReverieASRService() # Primary
        # self.backup_asr_service = GoogleSTTService() # Secondary
        self.tts_service = ElevenLabsTTSService()
        self.llm_service = LLMService()

    async def process_audio(self, audio_chunk):
        """
        Receives audio chunk, sends to ASR, gets text, sends to LLM, gets response, sends to TTS, yields audio.
        Note: This is a simplified sequential flow. Real-time requires async generators and interrupt handling.
        """
        # 1. ASR
        # For simplicity in this non-streaming mock, we assume complete utterances or implement a VAD buffer here
        transcribed_text = await self.asr_service.transcribe_stream(audio_chunk)
        
        if transcribed_text:
            print(f"User: {transcribed_text}")
            
            # 2. LLM
            llm_response = await self.llm_service.get_response(transcribed_text)
            print(f"Agent: {llm_response}")

            # 3. TTS
            async for audio_chunk in self.tts_service.generate_speech(llm_response):
                yield audio_chunk

    async def run_conversation(self, websocket):
        """
        Main loop for handling the websocket connection
        """
        try:
            while True:
                # Receive audio from client
                # This assumes client sends bytes. If text (for debug), handle accordingly.
                data = await websocket.receive_bytes()
                
                # Process
                async for response_audio in self.process_audio(data):
                    await websocket.send_bytes(response_audio)
                    
        except Exception as e:
            print(f"Conversation error: {e}")
