import json
import os
from datetime import datetime
import logging

# Ensure logs directory exists
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
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

def _load_logs(log_file):
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                if content:
                    return json.loads(content)
        except json.JSONDecodeError:
            pass
    return {}

def _save_logs(log_file, logs):
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)

def log_call_start(call_id):
    """
    Initializes a log entry for a new call.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"call_{today}.json")
    
    logs = _load_logs(log_file)
    
    if call_id not in logs:
        logs[call_id] = {
            "start_time": datetime.now().isoformat(),
            "status": "active",
            "turns": [],
            "lead_info": None
        }
        _save_logs(log_file, logs)

def log_call_turn(call_id, direction, text, metadata=None):
    """
    Logs a single turn of the conversation.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"call_{today}.json")
    
    logs = _load_logs(log_file)
    
    if call_id not in logs:
        # Should have been initialized, but just in case
        log_call_start(call_id)
        logs = _load_logs(log_file) # Reload
    
    turn_entry = {
        "timestamp": datetime.now().isoformat(),
        "direction": direction, # 'user' or 'assistant'
        "text": text
    }
    if metadata:
        turn_entry["metadata"] = metadata
        
    logs[call_id]["turns"].append(turn_entry)
    _save_logs(log_file, logs)

def log_lead_info(call_id, lead_data):
    """
    Logs qualified lead information.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"call_{today}.json")
    
    logs = _load_logs(log_file)
    
    if call_id in logs:
        logs[call_id]["lead_info"] = lead_data
        _save_logs(log_file, logs)
