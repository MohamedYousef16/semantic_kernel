from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.ollama import OllamaPromptExecutionSettings
import json ,logging,uuid
from models import SessionLocal ,RequestStatus , ServiceRequestModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Plugin  
class DatabasePlugin:
    def __init__(self):
        pass
    
    @kernel_function(
        description="Create a new service request in database",
        name="create_request"
    )
    def create_service_request(
        self,
        service_name: str,
        user_data: str,
        session_id: str,
        namespace: str = "default"
    ) -> str:
        """Create service request using existing database functions"""
        try:
            user_data_dict = json.loads(user_data) if isinstance(user_data, str) else user_data
            
            db = SessionLocal()
            
            # إنشاء البيانات للطلب
            request_data = {
                "service_name": service_name,
                "user_data": user_data_dict,
                "session_id": session_id,
                "namespace": namespace
            }
            
            # إنشاء الطلب في قاعدة البيانات
            request_id = str(uuid.uuid4())
            db_request = ServiceRequestModel(
                request_id=request_id,
                service_name=request_data["service_name"],
                user_data=request_data["user_data"],
                session_id=request_data.get("session_id"),
                namespace=request_data.get("namespace", "default"),
                status=RequestStatus.PENDING
            )
            db.add(db_request)
            db.commit()
            db.refresh(db_request)
            db.close()
            
            return json.dumps({
                "status": "success",
                "request_id": db_request.request_id,
                "message": f"تم إرسال طلبك بنجاح! رقم الطلب: {db_request.request_id}"
            })
            
        except Exception as e:
            logger.error(f"Error creating service request: {e}")
            return json.dumps({
                "status": "error",
                "message": f"خطأ في إرسال الطلب: {str(e)}"
            })