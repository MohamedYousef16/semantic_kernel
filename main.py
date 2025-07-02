from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from semantic_kernel.functions.kernel_arguments import KernelArguments
from kernel.setup import SemanticKernelConfig
from semantic_kernel.connectors.memory.chroma import ChromaMemoryStore
import os
import logging
from pathlib import Path
from datetime import datetime
import aiofiles ,json
from semantic_kernel.contents import AuthorRole
from config import CHROMA_BASE_PATH
from models import ChatMessage, ChatResponse, RequestStatusUpdate ,SessionLocal ,RequestStatus , ServiceRequestModel
from agent.service_agent import SemanticKernelServiceAgent
from utils import sanitize_collection_name, get_request_by_id, get_requests_paginated, update_request_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document AI Service Agent - Semantic Kernel",
    description="Enhanced conversational AI agent with Semantic Kernel and function calling",
    version="4.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_sessions: Dict[str, Dict[str, Any]] = {}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """Enhanced chat endpoint with Semantic Kernel ChatHistory"""
    try:
        # Create session with chat history if doesn't exist
        if message.session_id not in chat_sessions:
            chat_sessions[message.session_id] = {
                'agent': SemanticKernelServiceAgent(message.session_id, message.namespace),
                'created_at': datetime.now(),
                'last_activity': datetime.now(),
                'message_count': 0
            }
        
        # Update session activity
        chat_sessions[message.session_id]['last_activity'] = datetime.now()
        chat_sessions[message.session_id]['message_count'] += 1
        
        agent = chat_sessions[message.session_id]['agent']
        response = await agent.process_message(message.message)
        
        # Clean up completed sessions
        if response.completed:
            del chat_sessions[message.session_id]
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return ChatResponse(
            response=f"❌ خطأ في المعالجة: {str(e)}",
            status="error"
        )
    

@app.get("/requests")
async def get_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[RequestStatus] = None,
    service_name: Optional[str] = None
):
    """Get paginated service requests with filters"""
    try:
        db = SessionLocal()
        skip = (page - 1) * limit
        requests, total = get_requests_paginated(
            db, skip=skip, limit=limit, 
            status=status, service_name=service_name
        )
        db.close()
        
        return {
            "requests": [
                {
                    "id": req.id,
                    "request_id": req.request_id,
                    "service_name": req.service_name,
                    "status": req.status,
                    "created_at": req.created_at.isoformat(),
                    "updated_at": req.updated_at.isoformat(),
                    "user_data": req.user_data,
                    "session_id": req.session_id,
                    "namespace": req.namespace,
                    "notes": req.notes
                } for req in requests
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"Error getting requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    namespace: str = Form("default"),
):
    """Upload and process documents for semantic memory with improved persistence"""
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.txt', '.docx', '.doc'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"نوع الملف غير مدعوم. الأنواع المدعومة: {', '.join(allowed_extensions)}"
            )
        
        # Create namespace directory for temporary files
        temp_dir = Path("temp") / namespace
        temp_dir.mkdir(parents=True, exist_ok=True)

        # تحديد اسم المجموعة وتنظيفه
        raw_collection_name = f"documents_{namespace}"
        collection_name = sanitize_collection_name(raw_collection_name)
        
        # Save uploaded file temporarily
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = temp_dir / safe_filename
        
        async with aiofiles.open(file_path, 'wb') as buffer:
            content = await file.read()
            await buffer.write(content)
        
        logger.info(f"File saved temporarily: {file_path}")
        
        # Initialize Semantic Kernel for processing
        sk_config = SemanticKernelConfig()
        
        # Process document using DocumentPlugin
        arguments = KernelArguments(
            file_path=str(file_path),
            namespace=namespace,
            collection_name=collection_name,
            kernel=sk_config.kernel
        )
        
        result = await sk_config.kernel.invoke(
            plugin_name="document",
            function_name="process_document",
            arguments=arguments
        )
        
        processing_result = json.loads(str(result))
        
        # Clean up temporary file
        try:
            file_path.unlink()
            logger.info(f"Temporary file cleaned up: {file_path}")
        except Exception as cleanup_error:
            logger.warning(f"Could not clean up temporary file: {cleanup_error}")
        
        # Verify the collection was created
        try:
            memory_store = ChromaMemoryStore(persist_directory=CHROMA_BASE_PATH)
            collections = await memory_store.get_collections()
            logger.info(f"Collections after upload: {collections}")
        except Exception as verify_error:
            logger.warning(f"Could not verify collections: {verify_error}")
        
        return {
            "message": "تم رفع الملف ومعالجته بنجاح",
            "filename": file.filename,
            "namespace": namespace,
            "collection_name": collection_name,
            "processing_result": processing_result,
            "timestamp": timestamp
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        # Clean up file if exists
        if 'file_path' in locals() and file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"خطأ في رفع الملف: {str(e)}")
    
@app.get("/collections/{namespace}")
async def get_collections_for_namespace(namespace: str):
    """Get all collections for a specific namespace"""
    try:
        # Initialize memory store
        memory_store = ChromaMemoryStore(persist_directory=CHROMA_BASE_PATH)
        
        # Get all collections
        collections = await memory_store.get_collections()
        
        # Filter collections for this namespace
        namespace_collections = [
            col for col in collections 
            if col.startswith(f"documents_{namespace}") or col == f"documents_{namespace}"
        ]
        
        return {
            "namespace": namespace,
            "collections": namespace_collections,
            "total_collections": len(collections),
            "all_collections": collections
        }
        
    except Exception as e:
        logger.error(f"Error getting collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 5. إضافة endpoint لفحص محتوى Collection معينة
@app.get("/collections/{namespace}/{collection_name}/documents")
async def get_collection_documents(namespace: str, collection_name: str, limit: int = 10):
    """Get documents from a specific collection"""
    try:
        # Initialize services
        sk_config = SemanticKernelConfig()
        
        if not sk_config.semantic_memory:
            raise HTTPException(status_code=500, detail="Semantic memory not available")
        
        # Search for documents
        memories = await sk_config.semantic_memory.search(
            collection=collection_name,
            query="",  # Empty query to get all documents
            limit=limit
        )
        
        documents = [
            {
                "id": mem.id,
                "text": mem.text[:200] + "..." if len(mem.text) > 200 else mem.text,
                "description": mem.description,
                "relevance": mem.relevance
            }
            for mem in memories
        ]
        
        return {
            "namespace": namespace,
            "collection_name": collection_name,
            "documents": documents,
            "count": len(documents)
        }
        
    except Exception as e:
        logger.error(f"Error getting collection documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/requests/{request_id}")
async def get_request(request_id: str):
    """Get specific request by ID"""
    try:
        db = SessionLocal()
        request = get_request_by_id(db, request_id)
        db.close()
        
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return {
            "id": request.id,
            "request_id": request.request_id,
            "service_name": request.service_name,
            "status": request.status,
            "created_at": request.created_at.isoformat(),
            "updated_at": request.updated_at.isoformat(),
            "user_data": request.user_data,
            "session_id": request.session_id,
            "namespace": request.namespace,
            "notes": request.notes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/requests/{request_id}/status")
async def update_request_status_endpoint(request_id: str, status_update: RequestStatusUpdate):
    """Update request status"""
    try:
        db = SessionLocal()
        updated_request = update_request_status(
            db, request_id, status_update.status, status_update.notes
        )
        db.close()
        
        if not updated_request:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return {
            "message": "Request status updated successfully",
            "request_id": updated_request.request_id,
            "new_status": updated_request.status,
            "updated_at": updated_request.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating request status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get service request statistics with enhanced error handling"""
    db = None
    try:
        db = SessionLocal()
        
        # Basic counts with error handling
        total_requests = db.query(ServiceRequestModel).count()
        pending_requests = db.query(ServiceRequestModel).filter(
            ServiceRequestModel.status == RequestStatus.PENDING
        ).count()
        completed_requests = db.query(ServiceRequestModel).filter(
            ServiceRequestModel.status == RequestStatus.COMPLETED
        ).count()
        in_progress_requests = db.query(ServiceRequestModel).filter(
            ServiceRequestModel.status == RequestStatus.IN_PROGRESS
        ).count()
        rejected_requests = db.query(ServiceRequestModel).filter(
            ServiceRequestModel.status == RequestStatus.REJECTED
        ).count()
        cancelled_requests = db.query(ServiceRequestModel).filter(
            ServiceRequestModel.status == RequestStatus.CANCELLED
        ).count()
        
        # Service distribution with proper SQLAlchemy syntax
        try:
            from sqlalchemy import func
            service_stats = db.query(
                ServiceRequestModel.service_name,
                func.count(ServiceRequestModel.id).label('count')
            ).group_by(ServiceRequestModel.service_name).all()
            
            service_distribution = [
                {
                    "service_name": stat.service_name or "غير محدد", 
                    "count": stat.count
                } 
                for stat in service_stats
            ]
        except Exception as service_error:
            logger.error(f"Error getting service distribution: {service_error}")
            service_distribution = []
        
        # Recent requests (last 7 days) for trend analysis
        try:
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            recent_requests = db.query(ServiceRequestModel).filter(
                ServiceRequestModel.created_at >= week_ago
            ).count()
        except Exception as recent_error:
            logger.error(f"Error getting recent requests: {recent_error}")
            recent_requests = 0
        
        return {
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "completed_requests": completed_requests,
            "in_progress_requests": in_progress_requests,
            "rejected_requests": rejected_requests,
            "cancelled_requests": cancelled_requests,
            "recent_requests_week": recent_requests,
            "service_distribution": service_distribution,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Database connection or query error",
                "message": str(e),
                "type": type(e).__name__
            }
        )
    finally:
        if db:
            db.close()





@app.get("/namespaces")
async def get_namespaces():
    """Get all available namespaces"""
    try:
        namespaces = [d for d in os.listdir(CHROMA_BASE_PATH) 
                     if os.path.isdir(os.path.join(CHROMA_BASE_PATH, d))]
        return {"namespaces": namespaces}
    except Exception as e:
        logger.error(f"Error getting namespaces: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting namespaces: {str(e)}"}
        )

@app.get("/sessions")
async def get_active_sessions():
    """Get all active chat sessions with detailed information"""
    session_details = {}
    
    for session_id, session_data in chat_sessions.items():
        agent = session_data['agent']
        session_details[session_id] = {
            "created_at": session_data['created_at'].isoformat(),
            "last_activity": session_data['last_activity'].isoformat(),
            "message_count": session_data['message_count'],
            "state": agent.state,
            "namespace": agent.namespace,
            "service_info": agent.service_info,
            "collected_fields": len(agent.collected_data),
            "total_required_fields": len(agent.required_fields),
            "chat_history_length": len(agent.chat_history.messages)
        }
    
    return {
        "active_sessions": len(chat_sessions),
        "sessions": session_details
    }

@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get chat history for a specific session"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent = chat_sessions[session_id]['agent']
    history = []
    
    for msg in agent.chat_history.messages:
        history.append({
            "role": "user" if msg.role == AuthorRole.USER else "assistant",
            "content": msg.content,
            "timestamp": getattr(msg, 'timestamp', None)
        })
    
    return {
        "session_id": session_id,
        "history": history,
        "message_count": len(history),
        "session_info": {
            "created_at": chat_sessions[session_id]['created_at'].isoformat(),
            "last_activity": chat_sessions[session_id]['last_activity'].isoformat(),
            "total_messages": chat_sessions[session_id]['message_count']
        }
    }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)