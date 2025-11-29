import json
import os
from datetime import datetime
import logging

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(ch)
        
    return logger

def log_call_turn(direction, user_transcript, gpt_response, language="en"):
    """
    Logs a single turn of the conversation to a JSON file.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"call_{today}.json")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "direction": direction,
        "user_transcript": user_transcript,
        "gpt_response": gpt_response,
        "language": language
    }
    
    # Append to list in file, or create new list
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                if content:
                    logs = json.loads(content)
        except json.JSONDecodeError:
            pass
            
    logs.append(log_entry)
    
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)
