from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import CallLog, CallTurn

async def log_call_start(stream_sid: str):
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                call = CallLog(stream_sid=stream_sid, status="active")
                session.add(call)
    except Exception as e:
        print(f"Error logging call start: {e}")

async def log_call_turn(stream_sid: str, direction: str, text: str, metadata: dict = None):
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                turn = CallTurn(
                    stream_sid=stream_sid,
                    direction=direction,
                    text=text,
                    metadata_json=metadata
                )
                session.add(turn)
    except Exception as e:
        print(f"Error logging call turn: {e}")

async def log_lead_info(stream_sid: str, lead_data: dict):
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(select(CallLog).where(CallLog.stream_sid == stream_sid))
                call = result.scalars().first()
                if call:
                    call.lead_info = lead_data
    except Exception as e:
        print(f"Error logging lead info: {e}")
