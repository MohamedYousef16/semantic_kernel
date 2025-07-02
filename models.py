from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, Column, String, JSON, DateTime, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from config import DATABASE_URL, RequestStatus

Base = declarative_base()

class ServiceRequestModel(Base):
    __tablename__ = "service_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, index=True)
    service_name = Column(String(128))
    status = Column(String(32), default=RequestStatus.PENDING)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    user_data = Column(JSON)
    session_id = Column(String(64))
    namespace = Column(String(64), default="default")
    notes = Column(Text, nullable=True)

# Pydantic models
class ChatMessage(BaseModel):
    session_id: str
    message: str
    namespace: str = "default"

class ChatResponse(BaseModel):
    response: str
    status: str
    service_identified: bool = False
    service_info: Optional[Dict] = None
    next_field: Optional[str] = None
    completed: bool = False
    validation_error: Optional[str] = None

class ServiceRequestData(BaseModel):
    service_name: str
    user_data: Dict[str, Any]

class RequestStatusUpdate(BaseModel):
    request_id: str
    status: RequestStatus
    notes: Optional[str] = None

class RequestQuery(BaseModel):
    page: int = 1
    limit: int = 10
    status: Optional[RequestStatus] = None
    service_name: Optional[str] = None

class UploadResponse(BaseModel):
    message: str
    filename: str
    namespace: str
    collection: str
    processing_result: Dict[str, Any]

# Create DB engine and tables
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)