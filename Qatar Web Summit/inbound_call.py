import json
import base64
import asyncio
from fastapi import APIRouter, WebSocket, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Connect

from transcriber import Transcriber
from gpt_logic import GPTLogic
from tts_engine import TTSEngine
from utils.logger import log_call_start, log_call_turn

router = APIRouter()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Timing configuration (in seconds)
INTERRUPT_SETTLE_DELAY = 0.05      # Brief pause after interrupt flag is set
RESPONSE_START_DELAY = 0.02        # Minimal delay before starting TTS
AUDIO_CHUNK_DELAY = 0              # No delay between audio chunks (stream continuously)


@router.post("/incoming-call")
async def incoming_call(request: Request):
    """Handle incoming calls from Twilio."""
    response = VoiceResponse()
    response.answer()
    response.say("Connecting you to the Qatar Web Summit Guide.", voice="alice")
    connect = Connect()
    connect.stream(url=f"wss://{request.headers.get('host')}/media-stream")
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


@router.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """
    Handle the WebSocket stream from Twilio with optimized:
    - Interruption handling
    - Response latency
    - Audio streaming
    """
    await websocket.accept()
    print("═══════════════════════════════════════")
    print("  QATAR WEB SUMMIT GUIDE - CALL START")
    print("═══════════════════════════════════════")

    # Initialize components
    transcriber = Transcriber()
    gpt = GPTLogic()
    tts = TTSEngine()
    
    try:
        await transcriber.connect()
    except Exception as e:
        print(f"✗ Could not connect to transcriber: {e}")
        await websocket.close()
        return

    # State management
    stream_sid = None
    greeting_sent = asyncio.Event()
    
    # Interruption handling
    is_playing = asyncio.Event()
    interrupt_flag = asyncio.Event()
    response_lock = asyncio.Lock()  # Prevent overlapping responses

    # Initial greeting
    INITIAL_GREETING = (
        "Welcome to Qatar Web Summit in Doha! "
        "The event runs February 1st through 4th, 2026 at the Doha Exhibition and Convention Center. "
        "I can help you with speakers, startups, sessions, or navigating the event. "
        "What would you like to know?"
    )

    async def send_audio(text: str) -> bool:
        """
        Stream TTS audio to Twilio with interrupt checking.
        Returns True if completed, False if interrupted.
        """
        nonlocal stream_sid
        
        if not text or not text.strip():
            return True
        
        is_playing.set()
        transcriber.set_speaking(True)
        
        try:
            async for audio_chunk in tts.generate_audio(text):
                # Check for interruption before each chunk
                if interrupt_flag.is_set():
                    print("🛑 Audio interrupted")
                    # Clear Twilio's audio buffer
                    if stream_sid:
                        try:
                            await websocket.send_text(json.dumps({
                                "event": "clear",
                                "streamSid": stream_sid
                            }))
                        except:
                            pass
                    return False
                
                # Send audio chunk
                if stream_sid:
                    await websocket.send_text(json.dumps({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": base64.b64encode(audio_chunk).decode("ascii")
                        }
                    }))
            
            return True  # Completed without interruption
            
        finally:
            is_playing.clear()
            transcriber.set_speaking(False)

    async def send_greeting():
        """Send initial greeting when stream starts."""
        nonlocal stream_sid
        await greeting_sent.wait()
        
        if stream_sid:
            print("🎙 Sending greeting...")
            await log_call_turn(stream_sid, "assistant", INITIAL_GREETING)
            completed = await send_audio(INITIAL_GREETING)
            if completed:
                gpt.mark_branding_delivered()  # Greeting counts as first response
                print("✓ Greeting complete")
            else:
                print("⚡ Greeting interrupted")

    async def receive_audio():
        """Receive audio from Twilio and forward to transcriber."""
        nonlocal stream_sid
        try:
            async for message in websocket.iter_text():
                data = json.loads(message)
                
                if data['event'] == 'start':
                    stream_sid = data['start']['streamSid']
                    call_sid = data['start'].get('callSid', 'unknown')
                    print(f"📞 Stream: {stream_sid[:20]}...")
                    await log_call_start(stream_sid)
                    greeting_sent.set()
                    
                elif data['event'] == 'media':
                    chunk = base64.b64decode(data['media']['payload'])
                    await transcriber.send_audio(chunk)
                    
                elif data['event'] == 'stop':
                    print("📞 Call ended by user")
                    break
                    
        except Exception as e:
            print(f"⚠ Error in receive_audio: {e}")

    async def process_speech():
        """Process transcriptions and generate responses."""
        nonlocal stream_sid
        
        last_was_interrupted = False
        
        try:
            async for event_type, transcript in transcriber.get_transcription():
                
                if event_type == "INTERRUPT":
                    # ═══════════════════════════════════════
                    # INTERRUPTION FLOW
                    # ═══════════════════════════════════════
                    print(f"\n⚡ INTERRUPT: '{transcript}'")
                    
                    # Signal to stop current audio
                    interrupt_flag.set()
                    await asyncio.sleep(INTERRUPT_SETTLE_DELAY)
                    interrupt_flag.clear()
                    
                    # Wait for any current response to finish stopping
                    async with response_lock:
                        last_was_interrupted = True
                        
                        # Log user input
                        if stream_sid:
                            await log_call_turn(stream_sid, "user", transcript)
                        
                        # Generate response (with branding retry)
                        print("🤖 Generating response...")
                        gpt_response, _ = await gpt.generate_response(
                            transcript, 
                            was_interrupted=True
                        )
                        print(f"💬 Response: {gpt_response[:80]}...")
                        
                        # Log and send
                        if stream_sid:
                            await log_call_turn(stream_sid, "assistant", gpt_response)
                        
                        await asyncio.sleep(RESPONSE_START_DELAY)
                        completed = await send_audio(gpt_response)
                        
                        if completed:
                            gpt.mark_branding_delivered()
                            last_was_interrupted = False
                    
                elif event_type == "SPEECH":
                    # ═══════════════════════════════════════
                    # NORMAL SPEECH FLOW
                    # ═══════════════════════════════════════
                    
                    # Only process if not currently playing
                    if is_playing.is_set():
                        print(f"[Buffered] '{transcript}'")
                        continue
                    
                    print(f"\n🗣 USER: '{transcript}'")
                    
                    async with response_lock:
                        # Log user input
                        if stream_sid:
                            await log_call_turn(stream_sid, "user", transcript)
                        
                        # Generate response
                        print("🤖 Generating response...")
                        gpt_response, _ = await gpt.generate_response(
                            transcript,
                            was_interrupted=last_was_interrupted
                        )
                        print(f"💬 Response: {gpt_response[:80]}...")
                        
                        # Log and send
                        if stream_sid:
                            await log_call_turn(stream_sid, "assistant", gpt_response)
                        
                        await asyncio.sleep(RESPONSE_START_DELAY)
                        completed = await send_audio(gpt_response)
                        
                        if completed:
                            gpt.mark_branding_delivered()
                            last_was_interrupted = False
                        else:
                            last_was_interrupted = True
                        
        except Exception as e:
            print(f"⚠ Error in process_speech: {e}")
            import traceback
            traceback.print_exc()

    # ═══════════════════════════════════════
    # RUN CONCURRENT TASKS
    # ═══════════════════════════════════════
    try:
        await asyncio.gather(
            receive_audio(),
            process_speech(),
            send_greeting()
        )
    except Exception as e:
        print(f"⚠ Connection error: {e}")
    finally:
        await transcriber.close()
        print("═══════════════════════════════════════")
        print("  CALL ENDED")
        print("═══════════════════════════════════════")
