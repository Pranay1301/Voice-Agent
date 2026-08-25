# AI Voice Sales Agent

A production-ready AI voice sales agent for real estate that conducts natural phone conversations in Hindi, English, and Hinglish. Built with Twilio, Deepgram, Groq, and ElevenLabs.

## Features
- Natural voice conversations in Hindi/English/Hinglish
- Real-time speech recognition (Deepgram Nova-3)
- Ultra-low latency LLM responses (Groq)
- Natural text-to-speech (ElevenLabs)
- Structured lead qualification (HOT/WARM/COLD)
- Mid-call actions (WhatsApp, meeting booking)
- Post-call processing (email, summary)
- Real-time dashboard with live transcript
- Complete call safety (NO automatic dialing)
- Test mode for development
- Provider abstraction for easy swapping

## Architecture
```
Dashboard -> Backend -> Twilio Voice -> Media Streams (WebSocket)
                         |
                    Deepgram (ASR) -> Groq (LLM) -> ElevenLabs (TTS)
                         |
                    Decision Engine -> Action Engine -> WhatsApp/Email
```

## Prerequisites
- Node.js >= 18
- Twilio account (trial OK)
- Deepgram account (free credits)
- Groq account (free tier)
- ElevenLabs account (free tier)
- ngrok (for local development)

## Quick Start

### 1. Clone and Install
```bash
git clone https://github.com/Pranay1301/Voice-Agent.git
cd Voice-Agent

# Backend
cd backend
npm install
cp ../.env.example .env

# Frontend
cd ../frontend
npm install
```

### 2. Configure Environment
Edit backend/.env with your credentials:
```
# Required for real calls
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# Required for voice AI
DEEPGRAM_API_KEY=your_key
GROQ_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=your_voice_id

# For Twilio webhooks (use ngrok URL)
TWILIO_WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok-free.app

# Call safety (change to true only when ready to test)
ALLOW_OUTBOUND_CALLS=false
TEST_MODE=true
```

### 3. Set up ngrok (for Twilio webhooks)
```bash
ngrok http 3000
# Copy the https URL to TWILIO_WEBHOOK_BASE_URL in .env
```

### 4. Start the Application
```bash
# Terminal 1: Backend
cd backend && npm run dev

# Terminal 2: Frontend
cd frontend && npm run dev
```

### 5. Open Dashboard
Navigate to http://localhost:5173

## Test Mode
By default, TEST_MODE=true. In this mode:
- No real Twilio calls are placed
- You can type text messages in the dashboard
- Full conversation engine processes your text
- Lead qualification runs normally
- Actions are simulated (logged, not sent)

## Making a Real Test Call

1. Set up all credentials in .env
2. Start ngrok and update TWILIO_WEBHOOK_BASE_URL
3. Verify the target number in Twilio (trial accounts can only call verified numbers)
4. Set ALLOW_OUTBOUND_CALLS=true
5. Set TEST_MODE=false
6. Restart the backend
7. Open dashboard
8. Enter the target phone number
9. Click "START OUTBOUND TEST CALL"
10. Confirm the call in the dialog
11. The system will call the number via Twilio

## Call Safety
The system has multiple layers preventing automatic calls:
- ALLOW_OUTBOUND_CALLS defaults to false
- REQUIRE_MANUAL_CALL_TRIGGER must be true
- UI requires explicit button click + confirmation dialog
- Backend validates confirmation token (one-time use)
- No startup calls, no webhook-triggered calls
- No scheduled calls without human authorization

## Technology Stack
| Component | Provider | Notes |
|-----------|----------|-------|
| Telephony | Twilio | Voice + Media Streams |
| ASR | Deepgram | Nova-3, streaming, multilingual |
| LLM | Groq | llama-3.3-70b-versatile, free tier |
| TTS | ElevenLabs | eleven_flash_v2_5, streaming |
| Database | SQLite | Zero-dependency, file-based |
| Frontend | React + Vite | Real-time dashboard |
| Email | Nodemailer | SMTP |
| WhatsApp | Meta Cloud API | When configured |

## Project Structure
```
├── backend/
│   ├── src/
│   │   ├── index.js              # Server entry point
│   │   ├── config/               # Environment, database
│   │   ├── routes/               # API endpoints
│   │   ├── services/             # Business logic
│   │   ├── providers/            # AI service providers
│   │   ├── prompts/              # LLM prompts
│   │   ├── websocket/            # Twilio & dashboard WS
│   │   ├── middleware/           # Auth, safety
│   │   └── utils/                # Logger, audio, etc.
│   ├── knowledge/                # Knowledge base JSON
│   └── tests/                    # Test suites
├── frontend/
│   └── src/
│       ├── components/           # Dashboard UI
│       ├── hooks/                # WebSocket hook
│       ├── services/             # API client
│       └── styles/               # CSS
├── .env.example
└── README.md
```

## Running Tests
```bash
cd backend
npm test                  # All tests
npm run test:safety       # Call safety tests
npm run test:scenarios    # Scenario tests
```

## Free Tier Limits
| Provider | Free Tier | Notes |
|----------|-----------|-------|
| Groq | 30 RPM, 14.4K TPM (70B) | No credit card required |
| Deepgram | $200 credit | New accounts |
| ElevenLabs | 10,000 chars/month | Free plan |
| Twilio | Trial credits | Verified numbers only |

## License
MIT
