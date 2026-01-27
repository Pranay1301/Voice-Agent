import json
import base64
import asyncio
from fastapi import APIRouter, WebSocket, Request, Response
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect

from transcriber import Transcriber
from gpt_logic import GPTLogic
from tts_engine import TTSEngine
from utils.logger import log_call_start, log_call_turn, log_lead_info
from email_service import send_appointment_email

router = APIRouter()

@router.post("/incoming-call")
async def incoming_call(request: Request):
    """
    Handle incoming calls from Twilio.
    """
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
    Handle the WebSocket stream from Twilio.
    """
    await websocket.accept()
    print("Twilio connected")

    transcriber = Transcriber()
    gpt = GPTLogic()
    tts = TTSEngine()
    
    try:
        await transcriber.connect()
    except Exception as e:
        print(f"Could not connect to transcriber: {e}")
        await websocket.close()
        return

    stream_sid = None
    greeting_sent = asyncio.Event()

    # Initial greeting message
    INITIAL_GREETING = "Hi! I'm your real estate agent. Are you looking to buy or rent?"

    async def send_initial_greeting():
        """Send the initial greeting as soon as the stream starts."""
        nonlocal stream_sid
        await greeting_sent.wait()  # Wait for stream to start
        
        if stream_sid:
            print(f"Sending initial greeting...")
            await log_call_turn(stream_sid, "assistant", INITIAL_GREETING)
            
            # Generate TTS and stream back
            async for audio_chunk in tts.generate_audio(INITIAL_GREETING):
                media_message = {
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {
                        "payload": base64.b64encode(audio_chunk).decode("ascii")
                    }
                }
                await websocket.send_text(json.dumps(media_message))
            print("Initial greeting sent!")

    async def receive_from_twilio():
        nonlocal stream_sid
        try:
            async for message in websocket.iter_text():
                data = json.loads(message)
                if data['event'] == 'start':
                    stream_sid = data['start']['streamSid']
                    print(f"Stream started: {stream_sid}")
                    await log_call_start(stream_sid)
                    greeting_sent.set()  # Signal that stream is ready
                elif data['event'] == 'media':
                    media = data['media']
                    chunk = base64.b64decode(media['payload'])
                    await transcriber.send_audio(chunk)
                elif data['event'] == 'stop':
                    print("Stream stopped")
                    break
        except Exception as e:
            print(f"Error receiving from Twilio: {e}")

    async def send_to_twilio():
        nonlocal stream_sid
        try:
            async for transcript in transcriber.get_transcription():
                print(f"User: {transcript}")
                
                if stream_sid:
                    await log_call_turn(stream_sid, "user", transcript)
                
                # Get GPT response
                gpt_response, function_call = await gpt.generate_response(transcript)
                print(f"GPT: {gpt_response}")
                
                if stream_sid:
                    await log_call_turn(stream_sid, "assistant", gpt_response)
                    if function_call:
                        await log_lead_info(stream_sid, function_call)
                        # Send appointment confirmation email
                        if function_call.get("name") == "book_appointment":
                            appointment_data = function_call.get("args", {})
                            email_sent = send_appointment_email(appointment_data)
                            if email_sent:
                                print(f"📧 Appointment email sent to {appointment_data.get('email')}")

                # Generate TTS and stream back
                async for audio_chunk in tts.generate_audio(gpt_response):
                    if stream_sid:
                        media_message = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": base64.b64encode(audio_chunk).decode("ascii")
                            }
                        }
                        await websocket.send_text(json.dumps(media_message))
        except Exception as e:
            print(f"Error sending to Twilio: {e}")

    # Run tasks concurrently
    try:
        await asyncio.gather(receive_from_twilio(), send_to_twilio(), send_initial_greeting())
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        await transcriber.close()
        print("Connection closed")
