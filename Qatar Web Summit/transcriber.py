import os
import json
import re
import asyncio
import websockets
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# SPEECH FILTERING CONFIGURATION
# ============================================================================

# Noise/filler patterns to ignore (not real speech)
NOISE_PATTERNS = [
    r'^(uh+|um+|ah+|eh+|oh+|hm+|hmm+|mmm+|mhm+)$',  # Filler sounds
    r'^\s*$',  # Empty or whitespace only
]

# Short acknowledgments - only ignore if ALONE (not part of sentence)
ACKNOWLEDGMENT_WORDS = {'okay', 'ok', 'yeah', 'yes', 'no', 'right', 'sure', 'uh huh', 'mhm', 'yep', 'nope'}

# Meaningful short words that should NOT be filtered
MEANINGFUL_SHORT_WORDS = {
    'hello', 'hi', 'hey', 'help', 'stop', 'wait', 'what', 'who', 'when', 
    'where', 'how', 'why', 'thanks', 'thank', 'bye', 'goodbye', 'please',
    'speaker', 'speakers', 'startup', 'startups', 'event', 'time', 'schedule',
    'session', 'sessions', 'night', 'summit', 'ticket', 'tickets', 'venue'
}

# Strong interruption signals (user clearly wants to interrupt)
INTERRUPTION_SIGNALS = [
    'wait', 'stop', 'hold on', 'actually', 'but wait', 'excuse me', 
    'sorry but', 'one second', 'hang on', 'let me', 'can i', 'i have',
    'quick question', 'before you', 'what about', 'how about', 'instead'
]

# Thresholds
MIN_CHARS_FOR_SPEECH = 2           # Minimum characters for valid speech
MIN_WORDS_FOR_INTERRUPTION = 2     # Minimum words for an interruption during playback
MIN_CONFIDENCE = 0.65              # Minimum ASR confidence to accept
HIGH_CONFIDENCE = 0.85             # High confidence threshold


def normalize_text(text: str) -> str:
    """Normalize text by removing extra spaces and common ASR artifacts."""
    if not text:
        return ""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove leading fillers
    text = re.sub(r'^(uh+|um+|ah+|so+|like+|well+)\s+', '', text, flags=re.IGNORECASE)
    return text.strip()


def is_valid_speech(transcript: str, confidence: float = 1.0) -> bool:
    """
    Determines if a transcript is meaningful speech vs background noise.
    Returns True if this should be processed, False if it should be ignored.
    """
    if not transcript:
        return False
    
    text = normalize_text(transcript).lower()
    
    # Too short - likely noise
    if len(text) < MIN_CHARS_FOR_SPEECH:
        return False
    
    # Low confidence - likely noise
    if confidence < MIN_CONFIDENCE:
        return False
    
    # Check against noise patterns
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    
    # If it's just a single acknowledgment word, ignore it
    if text in ACKNOWLEDGMENT_WORDS:
        return False
    
    # Count actual words
    words = text.split()
    
    # Single word - only accept if it's meaningful
    if len(words) == 1:
        return text in MEANINGFUL_SHORT_WORDS or len(text) > 4
    
    return True


def is_interruption(transcript: str, confidence: float = 1.0) -> bool:
    """
    Determines if a transcript is a valid interruption (user wants to speak NOW).
    More strict than is_valid_speech - requires clear intent to interrupt.
    """
    if not is_valid_speech(transcript, confidence):
        return False
    
    text = normalize_text(transcript).lower()
    words = text.split()
    
    # Strong interruption signals - always interrupt
    for signal in INTERRUPTION_SIGNALS:
        if signal in text:
            return True
    
    # Question words at the start - likely a new question
    question_starters = ('what', 'who', 'when', 'where', 'how', 'why', 'is', 'are', 'can', 'do', 'does', 'will', 'could', 'would')
    if words and words[0] in question_starters:
        return True
    
    # If it ends with a question mark
    if text.endswith('?'):
        return True
    
    # If it's long enough (3+ words), it's intentional
    if len(words) >= MIN_WORDS_FOR_INTERRUPTION + 1:
        return True
    
    # High confidence short phrase - might be intentional
    if len(words) >= MIN_WORDS_FOR_INTERRUPTION and confidence >= HIGH_CONFIDENCE:
        return True
    
    return False


def should_wait_for_more(transcript: str) -> bool:
    """
    Determines if we should wait for more speech (user might not be done).
    Returns True if the utterance seems incomplete.
    """
    text = normalize_text(transcript).lower()
    
    # Ends with a conjunction or preposition - definitely not done
    incomplete_endings = ('and', 'or', 'but', 'the', 'a', 'an', 'to', 'for', 'with', 'about', 'like', 'of', 'in', 'on', 'at', 'is', 'are', 'was', 'were')
    words = text.split()
    if words and words[-1] in incomplete_endings:
        return True
    
    # Very short - might be more coming
    if len(words) <= 1 and text not in MEANINGFUL_SHORT_WORDS:
        return True
    
    return False


class Transcriber:
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise Exception("DEEPGRAM_API_KEY not found")
        self.connection = None
        self.is_speaking = False  # Track if agent is currently speaking
        self._pending_transcript = None  # Buffer for incomplete utterances
        self._pending_task = None  # Task for waiting on more speech

    async def connect(self):
        """
        Connects to Deepgram's WebSocket API with optimized settings for:
        - Low latency
        - Proper endpointing (waiting for user to finish)
        - Voice activity detection
        """
        # Optimized Deepgram settings
        url = (
            "wss://api.deepgram.com/v1/listen?"
            "encoding=mulaw&"
            "sample_rate=8000&"
            "model=nova-2&"
            "language=en&"
            "smart_format=true&"
            "punctuate=true&"
            "interim_results=false&"      # Only final results for stability
            "endpointing=400&"            # 400ms silence = end of utterance
            "utterance_end_ms=1200&"      # 1.2s to detect full utterance end
            "vad_events=true&"            # Voice Activity Detection
            "diarize=false&"              # Single speaker optimization
            "filler_words=false&"         # Let our code handle fillers
            "profanity_filter=false"      # Don't filter - we need raw input
        )
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        
        try:
            self.connection = await websockets.connect(
                url, 
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            print("✓ Connected to Deepgram (optimized: VAD + 400ms endpointing)")
            return self.connection
        except TypeError:
            # Fallback for older websockets versions
            self.connection = await websockets.connect(url, extra_headers=headers)
            print("✓ Connected to Deepgram (legacy mode)")
            return self.connection
        except Exception as e:
            print(f"✗ Failed to connect to Deepgram: {e}")
            raise e

    async def send_audio(self, chunk):
        """Sends an audio chunk to Deepgram for transcription."""
        if self.connection:
            try:
                await self.connection.send(chunk)
            except websockets.exceptions.ConnectionClosed:
                print("⚠ Deepgram connection closed while sending audio")
            except Exception as e:
                print(f"⚠ Error sending to Deepgram: {e}")

    async def get_transcription(self):
        """
        Receives transcription responses from Deepgram.
        Yields tuples of (event_type, transcript):
        - ("SPEECH", text) - Normal speech, agent should respond
        - ("INTERRUPT", text) - User interrupting, agent should stop and respond
        """
        if not self.connection:
            return
        
        try:
            async for message in self.connection:
                try:
                    data = json.loads(message)
                    
                    # Handle VAD speech start events
                    if data.get("type") == "SpeechStarted":
                        # User started speaking - if we're playing, prepare for potential interrupt
                        if self.is_speaking:
                            print("🎤 User speaking (agent playing)...")
                        continue
                    
                    # Handle utterance end events
                    if data.get("type") == "UtteranceEnd":
                        # Clear any pending transcript buffer
                        if self._pending_transcript:
                            text = self._pending_transcript
                            self._pending_transcript = None
                            if is_valid_speech(text):
                                yield ("SPEECH", text)
                        continue
                    
                    # Handle transcription results
                    if data.get("type") == "Results" and data.get("is_final", False):
                        alternatives = data.get("channel", {}).get("alternatives", [])
                        if not alternatives:
                            continue
                            
                        transcript = alternatives[0].get("transcript", "").strip()
                        confidence = alternatives[0].get("confidence", 0)
                        
                        if not transcript:
                            continue
                        
                        # Log for debugging
                        print(f"[ASR] '{transcript}' (conf: {confidence:.2f}, speaking: {self.is_speaking})")
                        
                        # Apply normalization
                        normalized = normalize_text(transcript)
                        if not normalized:
                            continue
                        
                        # Check if we should wait for more (incomplete utterance)
                        if should_wait_for_more(normalized) and not self.is_speaking:
                            # Buffer this and wait for more
                            if self._pending_transcript:
                                self._pending_transcript += " " + normalized
                            else:
                                self._pending_transcript = normalized
                            print(f"[Buffer] Waiting for more: '{self._pending_transcript}'")
                            continue
                        
                        # Combine with any pending transcript
                        if self._pending_transcript:
                            normalized = self._pending_transcript + " " + normalized
                            self._pending_transcript = None
                        
                        # Validate the speech
                        if not is_valid_speech(normalized, confidence):
                            print(f"[Filtered] '{normalized}' (noise/low confidence)")
                            continue
                        
                        # Determine if this is an interruption
                        if self.is_speaking:
                            if is_interruption(normalized, confidence):
                                print(f"⚡ INTERRUPT: '{normalized}'")
                                yield ("INTERRUPT", normalized)
                            else:
                                print(f"[Ignored during playback] '{normalized}'")
                        else:
                            print(f"✓ SPEECH: '{normalized}'")
                            yield ("SPEECH", normalized)
                                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"⚠ Error parsing Deepgram response: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("Deepgram connection closed")
        except Exception as e:
            print(f"⚠ Error receiving from Deepgram: {e}")

    def set_speaking(self, speaking: bool):
        """Set whether the agent is currently speaking (for interruption detection)."""
        self.is_speaking = speaking

    async def close(self):
        """Closes the Deepgram connection."""
        if self.connection:
            try:
                await self.connection.close()
                print("✓ Deepgram connection closed")
            except Exception as e:
                print(f"⚠ Error closing Deepgram connection: {e}")
