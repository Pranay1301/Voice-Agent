# Qatar Web Summit Voice Guide Agent

An AI-powered voice guide agent for **Web Summit Qatar 2026** (February 1-4, Doha). This agent provides real-time assistance to attendees via phone calls, answering questions about speakers, startups, sessions, and event navigation.

## 🎯 Features

### Core Capabilities
- **Real-time Voice Conversations** - Natural conversation via Twilio phone calls
- **Live Event Knowledge** - Scraped data from qatar.websummit.com
- **Doha Time Awareness** - Automatically provides current local time context
- **Speaker Information** - Details on 20+ confirmed speakers
- **Startup Directory** - 800+ featured startups and impact startups
- **Night Summit Info** - After-hours networking event details

### Production Optimizations
- **Smart Interruption Handling** - Stops when user speaks, ignores background noise
- **Utterance Detection** - Waits for user to complete sentences (400ms endpointing)
- **Speech Robustness** - Handles messy speech, bad grammar, filler words
- **Branding Integration** - Subtle Voice AI / MissedCall mentions
- **Low Latency** - Deepgram Nova-2 STT + Aura TTS for fast responses

## 🏗️ Tech Stack

| Component | Technology | Latency |
|-----------|------------|---------|
| Web Framework | FastAPI | - |
| Phone Gateway | Twilio | ~100ms |
| Speech-to-Text | Deepgram Nova-2 | ~200ms |
| LLM | Groq (Llama 3.3 70B) | ~500ms |
| Text-to-Speech | Deepgram Aura | ~150ms |
| Database | SQLite (async) | - |

**Total Response Time**: ~1 second (best-in-class for voice agents)

## 📁 Project Structure

```
Qatar Web Summit/
├── main.py              # FastAPI app entry point
├── inbound_call.py      # Twilio WebSocket handler + interruption logic
├── gpt_logic.py         # LLM with system prompt, knowledge, branding
├── knowledge_base.py    # Scraped Qatar Web Summit data
├── transcriber.py       # Deepgram STT with smart filtering
├── tts_engine.py        # Deepgram Aura TTS (optimized streaming)
├── database.py          # SQLite database setup
├── models.py            # Database models
├── config.py            # Configuration
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container deployment
└── utils/
    └── logger.py        # Call logging utilities
```

## 🔧 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
DEEPGRAM_TTS_VOICE=aura-athena-en  # Optional, default is athena
```

### 3. Run the Server
```bash
python main.py
```
Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Configure Twilio
Point your Twilio phone number's webhook to:
```
POST https://your-domain.com/incoming-call
```

## 🎤 Interruption Handling

The agent intelligently handles user interruptions:

| User Does | Agent Response |
|-----------|----------------|
| Says "wait" or "hold on" | Stops immediately, listens |
| Asks a new question | Stops, answers new question |
| Makes filler sounds ("uh", "um") | Ignores, continues speaking |
| Short acknowledgments ("ok", "yeah") | Ignores, continues speaking |
| Background noise | Ignores, continues speaking |

### Configuration (in `transcriber.py`)
```python
MIN_WORDS_FOR_INTERRUPTION = 2   # Words needed to trigger interrupt
MIN_CONFIDENCE = 0.65            # ASR confidence threshold
ENDPOINTING = 400                # ms of silence before finalizing
```

## 🗣️ Speech Robustness

The agent handles real-world messy speech:

| User Says | Agent Understands |
|-----------|-------------------|
| "uhh so like the uh speakers" | "Who are the speakers?" |
| "Stall where find startups?" | "Where are the startups?" |
| "I want to... um... the thing with..." | Most probable intent |

## 💬 Example Conversation

```
📞 Caller dials the Twilio number

🤖 Agent: "Welcome to Qatar Web Summit in Doha! The event runs 
          February 1st through 4th, 2026. I can help you with 
          speakers, startups, sessions, or navigating the event. 
          What would you like to know?"

👤 Caller: "Who are the speakers?"

🤖 Agent: "We have an incredible lineup including Tom Hale from 
          OpenAI, Eduardo Saverin, Mati Staniszewski from ElevenLabs, 
          and Colin Kaepernick. There's also Questlove and Logan Paul. 
          This kind of streamlined experience is what Voice AI builds—
          making organizations run smoother."

👤 Caller: [interrupts] "Wait, what about startups?"

🤖 Agent: [stops] "There are over 800 startups at Web Summit Qatar 
          covering AI, fintech, health tech, and climate tech. You 
          can explore them in the exhibition halls."
```

## 🏷️ Branding

The agent subtly incorporates branding for:
- **Voice AI** - AI automations for organizations (efficiency/automation topics)
- **MissedCall** - Voice AI agents (voice/conversation topics)

**Rules:**
- Branding is **mandatory on first response**
- If interrupted, branding is retried on next response
- After successful delivery, branding is used sparingly

## 📊 Performance Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| First Response Time | < 2s | ~1s |
| Interruption Latency | < 200ms | ~100ms |
| ASR Accuracy | > 90% | ~95% |
| Natural Conversation | Subjective | ✓ |

## 📝 License

Proprietary - Voice AI

---

Built with ❤️ by **Voice AI** and **MissedCall**
