# CRTG Voice Agent



<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Twilio](https://img.shields.io/badge/Twilio-Voice-F22F46?style=for-the-badge&logo=twilio&logoColor=white)](https://www.twilio.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![Deepgram](https://img.shields.io/badge/Deepgram-STT-13EF93?style=for-the-badge&logo=deepgram&logoColor=black)](https://deepgram.com/)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-000000?style=for-the-badge&logo=elevenlabs&logoColor=white)](https://elevenlabs.io/)

**A next-generation multilingual voice agent for real estate sales, powered by Generative AI.**

[Features](#-features) • [Architecture](#-architecture) • [Getting Started](#-getting-started) • [Usage](#-usage) • [Contributing](#-contributing)

</div>

---

## 🚀 Features

- **🗣️ Real-time Transcription**: Ultra-low latency speech-to-text using **Deepgram Nova-2**.
- **🧠 Intelligent Conversations**: Powered by **Google Gemini 1.5 Flash** (or GPT-4) for natural, context-aware dialogue.
- **🎙️ Human-like Voice**: Crystal clear, emotive text-to-speech via **ElevenLabs**.
- **📞 Inbound & Outbound**: Seamlessly handle calls via **Twilio Programmable Voice**.
- **📝 Structured Logging**: Automatically logs call metadata, transcripts, and qualified leads to JSON.
- **⚡ WebSocket Streaming**: Full-duplex audio streaming for sub-second response times.

## 🏗️ Architecture

```mermaid
graph TD
    User([User 📞]) <-->|PSTN| Twilio
    Twilio <-->|WebSocket Audio| Server[FastAPI Server]
    
    subgraph "AI Core"
        Server -->|Stream Audio| Deepgram[Deepgram STT]
        Deepgram -->|Transcript| Server
        
        Server -->|Prompt + Context| LLM[Gemini / GPT-4]
        LLM -->|Response Text| Server
        
        Server -->|Text| TTS[ElevenLabs TTS]
        TTS -->|Audio Stream| Server
    end
    
    Server -->|Logs & Leads| DB[(JSON Logs)]
```

## 🛠️ Getting Started

### Prerequisites

- Python 3.10+
- [ngrok](https://ngrok.com/) (for local testing)
- API Keys: Twilio, Deepgram, ElevenLabs, Google Gemini

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/Pranay1301/Voice-Agent.git
    cd Voice-Agent/crtg_voice_agent
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Copy `.env.example` to `.env` and fill in your keys:
    ```bash
    cp .env.example .env
    ```
    ```properties
    TWILIO_ACCOUNT_SID="your_sid"
    TWILIO_AUTH_TOKEN="your_token"
    TWILIO_PHONE_NUMBER="your_number"
    GEMINI_API_KEY="your_key"
    ELEVENLABS_API_KEY="your_key"
    ELEVENLABS_VOICE_ID="your_id"
    DEEPGRAM_API_KEY="your_key"
    DATABASE_URL="postgresql+asyncpg://user:pass@host/dbname"
    ```

## 🏃 Usage

### Local Development
```bash
uvicorn main:app --reload
```

### Docker Deployment
1.  **Build the image**
    ```bash
    docker build -t voice-agent .
    ```
2.  **Run the container**
    ```bash
    docker run --env-file .env -p 8000:8000 voice-agent
    ```

## 🏥 Health Check

Endpoint: `GET /health`
Response: `{"status": "ok"}`
- **Tables**: `call_logs`, `call_turns`
- **ORM**: SQLAlchemy + AsyncPG

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

<div align="center">
  <sub>Built with ❤️ by CRTG AI</sub>
</div>
