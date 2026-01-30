#!/bin/bash
# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from example..."
    cp .env.example .env 2>/dev/null || touch .env
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install requirements
pip install -r requirements.txt

# Start the server
echo "Starting CRTG Voice Agent on port 8000..."
echo "Make sure you have ngrok running in another terminal: ngrok http 8000"
echo "And update your Twilio Webhook URL to: https://<your-ngrok-url>/incoming-call"

python3 main.py
