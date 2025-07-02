from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.ollama import OllamaPromptExecutionSettings
import semantic_kernel as sk
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Conversation Plugin
class ConversationPlugin:
    def __init__(self):
        self.conversation_template = """
        أنت مساعد ذكي للخدمات الحكومية. تعامل مع المستخدم بشكل ودود ومهني.

        الحالة الحالية: {{$state}}
        المعلومات المجمعة: {{$collected_data}}
        الحقل التالي المطلوب: {{$next_field}}
        رسالة المستخدم: {{$user_message}}
        السياق السابق للمحادثة: {{$conversation_context}}

        اردد بطريقة واضحة ومفيدة باللغة العربية مع مراعاة السياق السابق للمحادثة.
        """
    
    @kernel_function(
        description="Generate conversational responses for service collection with chat history context",
        name="generate_response"
    )
    async def generate_response(
        self,
        state: str,
        collected_data: str,
        next_field: str,
        user_message: str,
        conversation_context: str = "",  # Add context parameter
        kernel: sk.Kernel = None
    ) -> str:
        """Generate contextual conversation responses with chat history"""
        try:
            # Get text completion service with proper settings
            text_completion = kernel.get_service("text_completion")
            prompt = self.conversation_template.replace("{{$state}}", state).replace("{{$collected_data}}", collected_data).replace("{{$next_field}}", next_field).replace("{{$user_message}}", user_message).replace("{{$conversation_context}}", conversation_context)
            
            # Create proper settings for the API call
            settings = OllamaPromptExecutionSettings()
            
            result = await text_completion.get_text_content(prompt, settings)
            return str(result)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "عذراً، حدث خطأ في معالجة طلبك. يرجى المحاولة مرة أخرى."