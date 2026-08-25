import os
import sys
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Twilio credentials
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

if not all([account_sid, auth_token, twilio_number]):
    print("Error: Twilio credentials not found in .env")
    sys.exit(1)

client = Client(account_sid, auth_token)

def make_call(to_number, server_url):
    """
    Initiates an outbound call.
    """
    try:
        call = client.calls.create(
            to=to_number,
            from_=twilio_number,
            url=f"{server_url}/incoming-call", # Re-use the TwiML from incoming call which connects to stream
            # Or we can define specific TwiML here
            # twiml=f'<Response><Connect><Stream url="wss://{server_url.replace("http://", "").replace("https://", "")}/media-stream" /></Connect></Response>'
        )
        print(f"Call initiated: {call.sid}")
    except Exception as e:
        print(f"Failed to make call: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python outbound_call.py <to_number> <server_url>")
        print("Example: python outbound_call.py +1234567890 https://my-ngrok-url.ngrok.io")
        sys.exit(1)

    to_number = sys.argv[1]
    server_url = sys.argv[2]
    
    make_call(to_number, server_url)
