from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.ollama import OllamaPromptExecutionSettings
import semantic_kernel as sk
import json ,logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceIdentificationPlugin:
    def __init__(self):
        self.service_template = """
        أنت وكيل ذكي متخصص في تحديد الخدمات الحكومية والإدارية.

        باستخدام المعلومات من الذاكرة والسياق المتاح، حدد الخدمة المحددة التي يطلبها المستخدم.

        رسالة المستخدم: {{$user_message}}
        السياق المتاح: {{$context}}

        أجب بتنسيق JSON فقط:
        {
          "service_name": "اسم الخدمة المحدد",
          "confidence": "عالي/متوسط/منخفض", 
          "required_fields": ["الحقل4","الحقل1", "الحقل2", "الحقل3","الحقل5"],
          "description": "وصف مختصر للخدمة",
          "estimated_processing_time": "المدة المتوقعة للمعالجة"
        }
        """
    
    @kernel_function(
        description="Identify the specific government service requested by the user",
        name="identify_service"
    )
    async def identify_service(
        self,
        user_message: str,
        context: str = "",
        kernel: sk.Kernel = None
    ) -> str:
        """Identify service using semantic memory and function calling"""
        try:
            # Get text completion service with proper settings
            text_completion = kernel.get_service("text_completion")
            prompt = self.service_template.replace("{{$user_message}}", user_message).replace("{{$context}}", context)
            
            # Create proper settings for the API call
            settings = OllamaPromptExecutionSettings()
            
            result = await text_completion.get_text_content(prompt, settings)
            return str(result)
        
        except Exception as e:
            logger.error(f"Error getting text completion service: {e}")
            return json.dumps({
                "service_name": "غير محدد",
                "confidence": "منخفض",
                "required_fields": [],
                "description": f"خطأ في تحديد الخدمة: {str(e)}",
                "estimated_processing_time": "غير محدد"
            })