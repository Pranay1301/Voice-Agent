# CRTG AI Voice Agent

A multilingual voice agent system for real estate sales in the GCC, built with FastAPI, Twilio, Deepgram, OpenAI GPT-4, and ElevenLabs.

## Features
- **Real-time Transcription**: Uses Deepgram for low-latency speech-to-text.
- **Natural Conversation**: Powered by OpenAI GPT-4 with a custom real estate sales prompt.
- **Human-like Voice**: Uses ElevenLabs for realistic text-to-speech.
- **Call Handling**: Supports both inbound and outbound calls via Twilio.
- **Logging**: Logs conversation turns and qualified leads.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Copy `.env.example` to `.env` and fill in your API keys:
    - Twilio (Account SID, Auth Token, Phone Number)
    - Gemini API Key
    - ElevenLabs API Key & Voice ID
    - Deepgram API Key

    > **How to get ElevenLabs Configuration:**
    > 1. Sign up/Login to [ElevenLabs](https://elevenlabs.io/).
    > 2. Click on your profile icon (top right) -> **Profile + API Key**.
    > 3. Click **Create New Key**.
    > 4. **Permissions Needed**:
    >    - **Text to Speech**: Set to **Access** (Required for generating audio).
    >    - **Voices**: Set to **Read** (Required to fetch voice details).
    >    - You can leave others as "No Access".
    > 5. Copy the **API Key**.
    > 6. Go to **Voices** -> **VoiceLab** or **Library**.
    > 7. Select a voice you like. Click the "ID" label (usually looks like a hash) to copy the **Voice ID**.

    > **How to get Deepgram Configuration:**
    > 1. Sign up/Login to [Deepgram Console](https://console.deepgram.com/).
    > 2. Go to **API Keys** in the left sidebar.
    > 3. Click **Create New API Key**.
    > 4. Give it a name (e.g., "Voice Agent") and assign "Member" permissions (or just leave default).
    > 5. Copy the generated **API Key**.

3.  **Run the Server**:
    ```bash
    uvicorn main:app --reload
    ```

4.  **Expose Local Server**:
    Use ngrok to expose your local server to the internet (required for Twilio webhooks):
    ```bash
    ngrok http 8000
    ```

5.  **Configure Twilio**:
    - Set the Voice Webhook URL for your Twilio number to `https://<your-ngrok-url>/incoming-call`.

## Usage

### Inbound Calls
Call your Twilio phone number. The agent will answer and start the conversation.

### Outbound Calls
Run the `outbound_call.py` script:
```bash
python outbound_call.py <target_phone_number> https://<your-ngrok-url>
```

## Logging
- Conversation logs are saved in `logs/call_YYYY-MM-DD.json`.
- Qualified leads are logged via GPT function calling (currently printed to console, can be extended to save to DB).
