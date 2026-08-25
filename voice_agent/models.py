from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from database import Base

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    stream_sid = Column(String, unique=True, index=True)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="active")
    lead_info = Column(JSON, nullable=True)
    
class CallTurn(Base):
    __tablename__ = "call_turns"

    id = Column(Integer, primary_key=True, index=True)
    stream_sid = Column(String, index=True) 
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    direction = Column(String) # user/assistant
    text = Column(Text)
    metadata_json = Column(JSON, nullable=True)
