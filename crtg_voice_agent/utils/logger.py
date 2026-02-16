import logging
import json
import asyncio
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from database import AsyncSessionLocal
from models import CallLog, CallTurn

logger = logging.getLogger(__name__)

async def log_call_start(stream_sid: str):
    """Log the start of a call session."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                call = CallLog(
                    stream_sid=stream_sid, 
                    status="active",
                    start_time=datetime.utcnow()
                )
                session.add(call)
        logger.info(f"Call started: {stream_sid}")
    except SQLAlchemyError as e:
        logger.error(f"Database error logging call start: {e}")
    except Exception as e:
        logger.error(f"Unexpected error logging call start: {e}")

async def log_call_turn(stream_sid: str, direction: str, text: str, metadata: dict = None):
    """Log individual call turns (user or assistant messages)."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                turn = CallTurn(
                    stream_sid=stream_sid,
                    direction=direction,
                    text=text,
                    timestamp=datetime.utcnow(),
                    metadata_json=json.dumps(metadata) if metadata else None
                )
                session.add(turn)
        logger.debug(f"Call turn logged: {stream_sid} - {direction} - {text[:50]}...")
    except SQLAlchemyError as e:
        logger.error(f"Database error logging call turn: {e}")
    except Exception as e:
        logger.error(f"Unexpected error logging call turn: {e}")

async def log_lead_info(stream_sid: str, lead_data: dict):
    """Log lead information extracted during the call."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(select(CallLog).where(CallLog.stream_sid == stream_sid))
                call = result.scalars().first()
                if call:
                    call.lead_info = lead_data
                    call.status = "completed"
                    call.end_time = datetime.utcnow()
        logger.info(f"Lead info logged for call: {stream_sid} - {lead_data}")
    except SQLAlchemyError as e:
        logger.error(f"Database error logging lead info: {e}")
    except Exception as e:
        logger.error(f"Unexpected error logging lead info: {e}")

async def log_error(stream_sid: str, error_type: str, error_message: str, component: str = "unknown"):
    """Log errors that occur during call processing."""
    try:
        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "component": component,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Try to find existing call log
                result = await session.execute(select(CallLog).where(CallLog.stream_sid == stream_sid))
                call = result.scalars().first()
                
                if call:
                    # Add error to call metadata
                    if call.metadata:
                        call_metadata = json.loads(call.metadata)
                    else:
                        call_metadata = {}
                    
                    if "errors" not in call_metadata:
                        call_metadata["errors"] = []
                    
                    call_metadata["errors"].append(error_data)
                    call.metadata = json.dumps(call_metadata)
                else:
                    # Create error log entry
                    error_log = CallTurn(
                        stream_sid=stream_sid,
                        direction="system",
                        text=f"ERROR: {error_type} - {error_message}",
                        timestamp=datetime.utcnow(),
                        metadata_json=json.dumps(error_data)
                    )
                    session.add(error_log)
        
        logger.error(f"Error logged: {stream_sid} - {component} - {error_type}: {error_message}")
    except SQLAlchemyError as e:
        logger.error(f"Database error logging error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error logging error: {e}")

async def log_performance_metric(stream_sid: str, metric_name: str, metric_value: float, unit: str = "ms"):
    """Log performance metrics for monitoring and optimization."""
    try:
        metric_data = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "unit": unit,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(select(CallLog).where(CallLog.stream_sid == stream_sid))
                call = result.scalars().first()
                
                if call:
                    if call.metadata:
                        call_metadata = json.loads(call.metadata)
                    else:
                        call_metadata = {}
                    
                    if "performance_metrics" not in call_metadata:
                        call_metadata["performance_metrics"] = []
                    
                    call_metadata["performance_metrics"].append(metric_data)
                    call.metadata = json.dumps(call_metadata)
        
        logger.debug(f"Performance metric logged: {stream_sid} - {metric_name}: {metric_value}{unit}")
    except SQLAlchemyError as e:
        logger.error(f"Database error logging performance metric: {e}")
    except Exception as e:
        logger.error(f"Unexpected error logging performance metric: {e}")

async def log_conversation_summary(stream_sid: str, summary_data: dict):
    """Log conversation summary for analytics and monitoring."""
    try:
        summary_data["timestamp"] = datetime.utcnow().isoformat()
        
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(select(CallLog).where(CallLog.stream_sid == stream_sid))
                call = result.scalars().first()
                
                if call:
                    if call.metadata:
                        call_metadata = json.loads(call.metadata)
                    else:
                        call_metadata = {}
                    
                    call_metadata["conversation_summary"] = summary_data
                    call.metadata = json.dumps(call_metadata)
        
        logger.info(f"Conversation summary logged: {stream_sid} - {summary_data}")
    except SQLAlchemyError as e:
        logger.error(f"Database error logging conversation summary: {e}")
    except Exception as e:
        logger.error(f"Unexpected error logging conversation summary: {e}")
