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

router = APIRouter()

@router.post("/incoming-call")
async def incoming_call(request: Request):
    """
    Handle incoming calls from Twilio.
    """
    response = VoiceResponse()
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

    async def receive_from_twilio():
        nonlocal stream_sid
        try:
            async for message in websocket.iter_text():
                data = json.loads(message)
                if data['event'] == 'start':
                    stream_sid = data['start']['streamSid']
                    print(f"Stream started: {stream_sid}")
                    log_call_start(stream_sid)
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
                    log_call_turn(stream_sid, "user", transcript)
                
                # Get GPT response
                gpt_response, function_call = await gpt.generate_response(transcript)
                print(f"GPT: {gpt_response}")
                
                if stream_sid:
                    log_call_turn(stream_sid, "assistant", gpt_response)
                    if function_call:
                        log_lead_info(stream_sid, function_call)

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
        await asyncio.gather(receive_from_twilio(), send_to_twilio())
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        await transcriber.close()
        print("Connection closed")
