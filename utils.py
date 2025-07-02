import re
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from models import ServiceRequestModel, RequestStatus
from datetime import datetime

def sanitize_collection_name(name: str) -> str:
    """Sanitize collection name for ChromaDB"""
    # Replace spaces and invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Ensure it starts and ends with alphanumeric
    sanitized = re.sub(r'^[^a-zA-Z0-9]+', '', sanitized)
    sanitized = re.sub(r'[^a-zA-Z0-9]+$', '', sanitized)
    
    # Ensure minimum length
    if len(sanitized) < 3:
        sanitized = f"collection_{sanitized}"
    
    # Ensure maximum length
    if len(sanitized) > 63:
        sanitized = sanitized[:63]
    
    # Ensure it doesn't end with non-alphanumeric after truncation
    sanitized = re.sub(r'[^a-zA-Z0-9]+$', '', sanitized)
    
    return sanitized or "default_collection"

def get_request_by_id(db: Session, request_id: str) -> Optional[ServiceRequestModel]:
    """Get request by ID"""
    return db.query(ServiceRequestModel).filter(ServiceRequestModel.request_id == request_id).first()

def get_requests_paginated(db: Session, skip: int = 0, limit: int = 10, 
                          status: Optional[RequestStatus] = None,
                          service_name: Optional[str] = None) -> Tuple[List[ServiceRequestModel], int]:
    """Get paginated requests with filters"""
    query = db.query(ServiceRequestModel)
    
    if status:
        query = query.filter(ServiceRequestModel.status == status)
    if service_name:
        query = query.filter(ServiceRequestModel.service_name.contains(service_name))
    
    total = query.count()
    requests = query.order_by(ServiceRequestModel.created_at.desc()).offset(skip).limit(limit).all()
    
    return requests, total

def update_request_status(db: Session, request_id: str, status: RequestStatus, notes: Optional[str] = None) -> Optional[ServiceRequestModel]:
    """Update request status"""
    db_request = get_request_by_id(db, request_id)
    if db_request:
        db_request.status = status
        db_request.updated_at = datetime.now()
        if notes:
            db_request.notes = notes
        db.commit()
        db.refresh(db_request)
    return db_request