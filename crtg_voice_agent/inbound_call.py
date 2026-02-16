import json
import base64
import asyncio
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.request_validator import RequestValidator

from transcriber import Transcriber
from gpt_logic import GPTLogic
from tts_engine import TTSEngine
from utils.logger import log_call_start, log_call_turn, log_lead_info
from utils.performance_monitor import performance_monitor
from email_service import send_appointment_email

router = APIRouter()
logger = logging.getLogger(__name__)

# Configuration
MAX_CALL_DURATION = 300  # 5 minutes max call duration
MAX_TRANSCRIPTION_RETRIES = 3
MAX_TTS_RETRIES = 2
INTERRUPT_THRESHOLD = 0.5  # seconds to wait before checking for interruption

class CallSession:
    """Manage individual call session state."""
    
    def __init__(self, stream_sid: str):
        self.stream_sid = stream_sid
        self.transcriber: Optional[Transcriber] = None
        self.gpt: Optional[GPTLogic] = None
        self.tts: Optional[TTSEngine] = None
        self.call_start_time = asyncio.get_event_loop().time()
        self.user_data: Dict[str, Any] = {}
        self.conversation_state = "greeting"
        self.is_active = True
        self.is_speaking = False
        self.interrupt_flag = asyncio.Event()
        self.audio_queue = asyncio.Queue()
        
    async def initialize(self):
        """Initialize all components for the call."""
        try:
            self.transcriber = Transcriber()
            await self.transcriber.connect()
            
            self.gpt = GPTLogic()
            self.tts = TTSEngine()
            
            logger.info(f"Call session initialized for stream: {self.stream_sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize call session: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources."""
        self.is_active = False
        self.interrupt_flag.set()  # Wake up any waiting tasks
        if self.transcriber:
            await self.transcriber.close()
        logger.info(f"Call session cleaned up for stream: {self.stream_sid}")

def validate_twilio_request(request: Request) -> bool:
    """Validate incoming Twilio request for security."""
    try:
        validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))
        url = str(request.url)
        signature = request.headers.get("X-Twilio-Signature", "")
        params = dict(request.query_params)
        
        return validator.validate(url, params, signature)
    except Exception as e:
        logger.error(f"Error validating Twilio request: {e}")
        return False

@router.post("/incoming-call")
async def incoming_call(request: Request):
    """
    Handle incoming calls from Twilio with security validation.
    """
    # Validate Twilio request
    if not validate_twilio_request(request):
        logger.warning("Invalid Twilio request received")
        raise HTTPException(status_code=403, detail="Invalid Twilio request")
    
    response = VoiceResponse()
    response.answer()  # Answers the call immediately
    response.say("Connecting you to the AI sales assistant.")
    connect = Connect()
    connect.stream(url=f"wss://{request.headers.get('host')}/media-stream")
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")

@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    Handle the WebSocket stream from Twilio with interrupt handling.
    """
    session = None
    stream_sid = None
    
    try:
        await websocket.accept()
        logger.info("Twilio WebSocket connection established")
        
        # Wait for stream start
        stream_sid = None
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            
            if data.get('event') == 'connected':
                logger.info("Received Twilio 'connected' event")
                continue
            elif data.get('event') == 'start':
                stream_sid = data['start']['streamSid']
                break
            else:
                logger.warning(f"Received unexpected event while waiting for start: {data.get('event')}")
                
        if not stream_sid:
             logger.error("Stream SID not found")
             return
        session = CallSession(stream_sid)
        
        # Initialize call session
        if not await session.initialize():
            await websocket.close(code=1011, reason="Service unavailable")
            return
        
        await log_call_start(stream_sid)
        logger.info(f"Call started: {stream_sid}")
        
        # Send initial greeting
        await send_greeting(websocket, session)
        
        # Handle call flow with interrupt capability
        await handle_call_flow_with_interrupts(websocket, session)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for stream: {stream_sid}")
    except Exception as e:
        logger.error(f"Error in media stream: {e}")
        if session:
            await session.cleanup()
    finally:
        if session:
            await session.cleanup()

async def send_greeting(websocket: WebSocket, session: CallSession):
    """Send initial greeting to the caller."""
    INITIAL_GREETING = "Hi! I'm your real estate agent. Are you looking to buy or rent?"
    
    try:
        await log_call_turn(session.stream_sid, "assistant", INITIAL_GREETING)
        
        # Generate TTS and stream back
        async for audio_chunk in session.tts.generate_audio(INITIAL_GREETING):
            if not session.is_active or session.interrupt_flag.is_set():
                logger.info("Greeting interrupted by user speech")
                break
                
            media_message = {
                "event": "media",
                "streamSid": session.stream_sid,
                "media": {
                    "payload": base64.b64encode(audio_chunk).decode("ascii")
                }
            }
            await websocket.send_text(json.dumps(media_message))
            
        logger.info(f"Initial greeting sent for stream: {session.stream_sid}")
    except Exception as e:
        logger.error(f"Error sending greeting: {e}")

async def handle_call_flow_with_interrupts(websocket: WebSocket, session: CallSession):
    """Handle the main call flow with interrupt capability."""
    
    # Start background tasks
    message_handler_task = asyncio.create_task(handle_incoming_messages(websocket, session))
    transcription_processor_task = asyncio.create_task(process_transcriptions(websocket, session))
    
    try:
        # Wait for either task to complete (call ended)
        await asyncio.wait(
            [message_handler_task, transcription_processor_task],
            return_when=asyncio.FIRST_COMPLETED
        )
    except Exception as e:
        logger.error(f"Error in call flow: {e}")
    finally:
        # Cancel remaining tasks
        message_handler_task.cancel()
        transcription_processor_task.cancel()
        
        try:
            await message_handler_task
            await transcription_processor_task
        except asyncio.CancelledError:
            pass

async def handle_incoming_messages(websocket: WebSocket, session: CallSession):
    """Handle incoming WebSocket messages and detect interruptions."""
    try:
        async for message in websocket.iter_text():
            if not session.is_active:
                break
                
            data = json.loads(message)
            
            if data['event'] == 'media':
                # Process audio
                media = data['media']
                chunk = base64.b64decode(media['payload'])
                await session.transcriber.send_audio(chunk)
                
                # Check if user is speaking while agent is talking
                # REMOVED: Do not interrupt on raw audio/media events as this triggers on silence/noise
                # if session.is_speaking:
                #     logger.info(f"User interruption detected in stream: {session.stream_sid}")
                #     session.interrupt_flag.set()
                
            elif data['event'] == 'stop':
                logger.info(f"Call stopped: {session.stream_sid}")
                session.is_active = False
                session.interrupt_flag.set()
                break
                
            elif data['event'] == 'mark':
                # Handle Twilio markers
                logger.debug(f"Received mark event: {data}")
                
    except Exception as e:
        logger.error(f"Error handling incoming messages: {e}")
        session.is_active = False
        session.interrupt_flag.set()

async def process_transcriptions(websocket: WebSocket, session: CallSession):
    """Process transcriptions and handle responses with interrupt capability."""
    try:
        async for transcript in session.transcriber.get_transcription():
            if not session.is_active:
                break
                
            logger.info(f"Transcript received: {transcript}")
            
            # Validate transcript
            if not transcript or len(transcript.strip()) < 2:
                continue
            
            # VALID INTERRUPTION: If we receive a transcript while speaking, stop the TTS
            if session.is_speaking:
                logger.info(f"Interruption triggered by transcript: {transcript}")
                session.interrupt_flag.set()
                # Give a brief moment for TTS to stop
                await asyncio.sleep(0.1)

            await log_call_turn(session.stream_sid, "user", transcript)
            
            # Clear interrupt flag for the new turn
            session.interrupt_flag.clear()
            
            # Generate GPT response with retry logic
            gpt_response, extracted_data = await generate_gpt_response_with_retry(
                session.gpt, transcript, MAX_TRANSCRIPTION_RETRIES
            )
            
            if gpt_response:
                await log_call_turn(session.stream_sid, "assistant", gpt_response)
                
                # Process extracted data
                if extracted_data:
                    session.user_data.update(extracted_data)
                    logger.info(f"Extracted data: {extracted_data}")
                
                # Send TTS response with interrupt capability
                await send_tts_response_with_interrupts(
                    websocket, session, gpt_response, session.stream_sid
                )
            
            # Check call duration
            current_time = asyncio.get_event_loop().time()
            if current_time - session.call_start_time > MAX_CALL_DURATION:
                logger.info(f"Call duration exceeded for stream: {session.stream_sid}")
                session.is_active = False
                break
                
    except Exception as e:
        logger.error(f"Error processing transcriptions: {e}")

async def send_tts_response_with_interrupts(websocket: WebSocket, session: CallSession, 
                                          text: str, stream_sid: str):
    """Send TTS response with interrupt capability."""
    session.is_speaking = True
    session.interrupt_flag.clear()
    
    try:
        async for audio_chunk in session.tts.generate_audio(text):
            # Check for interruption
            if session.interrupt_flag.is_set():
                logger.info(f"Response interrupted: {text[:30]}...")
                break
                
            media_message = {
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": base64.b64encode(audio_chunk).decode("ascii")
                }
            }
            await websocket.send_text(json.dumps(media_message))
            
            # Small delay to allow interruption checking
            await asyncio.sleep(0.01)
            
    except Exception as e:
        logger.error(f"TTS response failed: {e}")
    finally:
        session.is_speaking = False
        session.interrupt_flag.clear()

async def generate_gpt_response_with_retry(gpt: GPTLogic, transcript: str, max_retries: int) -> tuple:
    """Generate GPT response with retry logic."""
    for attempt in range(max_retries):
        try:
            response, data = await gpt.generate_response(transcript)
            if response:
                return response, data
        except Exception as e:
            logger.error(f"GPT generation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return "I'm having trouble responding. Please try again.", None
            await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
    
    return "Sorry, I didn't catch that. Could you please repeat?", None
