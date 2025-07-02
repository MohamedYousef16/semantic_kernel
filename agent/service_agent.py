import json
import logging
from typing import Dict
from semantic_kernel.functions.kernel_arguments import KernelArguments
from kernel.setup import SemanticKernelConfig
from models import ChatResponse
from utils import sanitize_collection_name
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents import AuthorRole

logger = logging.getLogger(__name__)


# SemanticKernelServiceAgent - Fixed identify_service method
class SemanticKernelServiceAgent:
    def __init__(self, session_id: str, namespace: str = "default"):
        self.session_id = session_id
        self.namespace = namespace
        self.state = "initial"
        self.service_info = None
        self.collected_data = {}
        self.current_field_index = 0
        self.required_fields = []
        self.validation_attempts = {}

        self.chat_history = ChatHistory()
        
        # Initialize Semantic Kernel
        self.sk_config = SemanticKernelConfig()
        self.kernel = self.sk_config.kernel
        
        # Setup memory for this namespace
        self.setup_namespace_memory()

    def add_user_message(self, message: str):
        """Add user message to chat history"""
        self.chat_history.add_message(
            ChatMessageContent(
                role=AuthorRole.USER,
                content=message
            )
        )
    
    def add_assistant_message(self, message: str):
        """Add assistant response to chat history"""
        self.chat_history.add_message(
            ChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content=message
            )
        )

    def get_conversation_context(self, last_n_messages: int = 5) -> str:
        """Get recent conversation context for better responses"""
        messages = self.chat_history.messages[-last_n_messages:] if len(self.chat_history.messages) > last_n_messages else self.chat_history.messages
        
        context = ""
        for msg in messages:
            role = "المستخدم" if msg.role == AuthorRole.USER else "المساعد"
            context += f"{role}: {msg.content}\n"
        
        return context
    
    def setup_namespace_memory(self):
        """Setup memory for specific namespace with collection verification"""
        try:
            self.memory_collection = f"documents_{self.namespace}"
            self.memory_collection = sanitize_collection_name(self.memory_collection)
            logger.info(f"Setup memory for namespace: {self.namespace}, collection: {self.memory_collection}")
        except Exception as e:
            logger.error(f"Error setting up namespace memory: {e}")
    
    async def identify_service(self, user_message: str) -> Dict:
        """Use Semantic Kernel function calling to identify service with improved collection handling"""
        try:
            context = ""
            
            # Search in memory with improved error handling
            try:
                if self.sk_config.semantic_memory:
                    # List available collections first
                    try:
                        collections = await self.sk_config.memory_store.get_collections()
                        logger.info(f"Available collections: {collections}")
                        
                        # Check if our collection exists
                        if self.memory_collection in collections:
                            logger.info(f"Found collection: {self.memory_collection}")
                            
                            # Search in the collection
                            memories = await self.sk_config.semantic_memory.search(
                                collection=self.memory_collection,
                                query=user_message,
                                limit=5
                            )
                            context = "\n".join([mem.text for mem in memories])
                            logger.info(f"Found {len(memories)} relevant memories")
                        else:
                            logger.warning(f"Collection {self.memory_collection} not found in {collections}")
                            
                            # Try to search in all available collections
                            for collection in collections:
                                if collection.startswith(f"documents_{self.namespace}") or collection.startswith("documents_"):
                                    try:
                                        memories = await self.sk_config.semantic_memory.search(
                                            collection=collection,
                                            query=user_message,
                                            limit=3
                                        )
                                        if memories:
                                            context += "\n".join([mem.text for mem in memories])
                                            logger.info(f"Found memories in alternate collection: {collection}")
                                            break
                                    except Exception as alt_search_error:
                                        logger.warning(f"Failed to search in {collection}: {alt_search_error}")
                                        continue
                    except Exception as collections_error:
                        logger.warning(f"Could not get collections: {collections_error}")
                        context = ""
                        
            except Exception as search_error:
                logger.warning(f"Could not search semantic memory: {search_error}")
                context = ""
            
            # Use service identification plugin
            arguments = KernelArguments(
                user_message=user_message,
                context=context,
                kernel=self.kernel
            )
            
            result = await self.kernel.invoke(
                plugin_name="service_id",
                function_name="identify_service",
                arguments=arguments
            )
            
            # Parse JSON result with better error handling
            try:
                service_data = json.loads(str(result))
                # Validate required fields exist
                if not all(key in service_data for key in ["service_name", "confidence", "required_fields"]):
                    raise ValueError("Invalid service data structure")
                    
                logger.info(f"Service identified: {service_data['service_name']} with confidence {service_data.get('confidence', 'unknown')}")
                
            except (json.JSONDecodeError, ValueError) as parse_error:
                logger.warning(f"Could not parse service identification result: {parse_error}")
                # Provide intelligent defaults based on user message
                service_data = {
                    "service_name": "خدمة غير محددة",
                    "confidence": "منخفض",
                    "required_fields": ["الاسم الكامل", "رقم الهوية", "رقم الجوال"],
                    "description": "خدمة عامة تتطلب معلومات أساسية",
                    "estimated_processing_time": "3-5 أيام عمل"
                }

            return service_data
            
        except Exception as e:
            logger.error(f"Error in service identification: {e}")
            return {
                "service_name": "خدمة غير محددة",
                "confidence": "منخفض",
                "required_fields": ["الاسم الكامل", "رقم الهوية"],
                "description": f"خطأ في تحديد الخدمة: {str(e)}",
                "estimated_processing_time": "غير محدد"
            }
    
    async def validate_input(self, field_name: str, value: str) -> tuple[bool, str]:
        """Use validation plugin for input validation"""
        try:
            arguments = KernelArguments(
                field_name=field_name,
                value=value
            )
            
            result = await self.kernel.invoke(
                plugin_name="validation",
                function_name="validate_field",
                arguments=arguments
            )
            
            validation_result = json.loads(str(result))
            return validation_result["is_valid"], validation_result["error_message"]
            
        except Exception as e:
            logger.error(f"Error in validation: {e}")
            return False, f"خطأ في التحقق: {str(e)}"
    
    async def create_service_request(self, service_name: str, user_data: Dict) -> Dict:
        """Use database plugin to create service request"""
        try:
            arguments = KernelArguments(
                service_name=service_name,
                user_data=json.dumps(user_data),
                session_id=self.session_id,
                namespace=self.namespace
            )
            
            result = await self.kernel.invoke(
                plugin_name="database",
                function_name="create_request",
                arguments=arguments
            )
            
            return json.loads(str(result))
            
        except Exception as e:
            logger.error(f"Error creating service request: {e}")
            return {
                "status": "error",
                "message": f"خطأ في إنشاء الطلب: {str(e)}"
            }
    
    async def generate_response(self, user_message: str) -> str:
        """Enhanced response generation with chat history context"""
        try:
            # Get conversation context
            conversation_context = self.get_conversation_context()
            
            arguments = KernelArguments(
                state=self.state,
                collected_data=json.dumps(self.collected_data),
                next_field=self.required_fields[self.current_field_index] if self.current_field_index < len(self.required_fields) else "",
                user_message=user_message,
                conversation_context=conversation_context,  # Add context
                kernel=self.kernel
            )
            
            result = await self.kernel.invoke(
                plugin_name="conversation", 
                function_name="generate_response",
                arguments=arguments
            )
            
            return str(result)
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "عذراً، حدث خطأ في معالجة طلبك."
     
    async def process_message(self, user_message: str) -> "ChatResponse":
        """Enhanced message processing with chat history"""
        try:
            # Add user message to chat history
            self.add_user_message(user_message)
            
            # Rest of your existing logic remains the same...
            if self.state == "initial":
                logger.info(f"Identifying service for message: {user_message}")
                service_info = await self.identify_service(user_message)
                
                self.service_info = service_info
                self.required_fields = service_info.get("required_fields", [])
                self.state = "service_identified"
                
                if self.required_fields:
                    self.state = "collecting_info"
                    first_field = self.required_fields[0]
                    response_text = f"✅ تم تحديد الخدمة: **{service_info['service_name']}**\n\n📝 {service_info['description']}\n\n⏱️ المدة المتوقعة: {service_info.get('estimated_processing_time', '3-5 أيام عمل')}\n\n🔹 يرجى تزويدي بالمعلومة التالية:\n**{first_field}**\n\n💡"
                    
                    # Add assistant response to chat history
                    self.add_assistant_message(response_text)
                    
                    return ChatResponse(
                        response=response_text,
                        status="success",
                        service_identified=True,
                        service_info=service_info,
                        next_field=first_field
                    )
                else:
                    result = await self.create_service_request(service_info['service_name'], {})
                    self.state = "completed"
                    response_text = f"✅ تم تحديد الخدمة: **{service_info['service_name']}**\n\n{result['message']}"
                    
                    # Add assistant response to chat history
                    self.add_assistant_message(response_text)
                    
                    return ChatResponse(
                        response=response_text,
                        status="success",
                        service_identified=True,
                        service_info=service_info,
                        completed=True
                    )
            
            elif self.state == "collecting_info":
                current_field = self.required_fields[self.current_field_index]
                
                # Validate input using Semantic Kernel
                is_valid, error_message = await self.validate_input(current_field, user_message)
                
                if not is_valid:
                    # Track validation attempts
                    if current_field not in self.validation_attempts:
                        self.validation_attempts[current_field] = 0
                    self.validation_attempts[current_field] += 1
                    
                    # Allow 3 attempts before skipping
                    if self.validation_attempts[current_field] >= 3:
                        response_text = f"❌ تم تجاوز عدد المحاولات المسموحة لـ **{current_field}**\n\n🔄 يرجى البدء من جديد أو الاتصال بالدعم الفني"
                        self.add_assistant_message(response_text)
                        
                        return ChatResponse(
                            response=response_text,
                            status="error",
                            validation_error=error_message
                        )
                    
                    response_text = f"❌ خطأ في **{current_field}**: {error_message}\n\n🔄 يرجى المحاولة مرة أخرى ({self.validation_attempts[current_field]}/3)\n\n💡"
                    self.add_assistant_message(response_text)
                    
                    return ChatResponse(
                        response=response_text,
                        status="validation_error",
                        validation_error=error_message,
                        next_field=current_field
                    )
                
                # Input is valid, save it
                self.collected_data[current_field] = user_message.strip()
                self.current_field_index += 1
                
                if self.current_field_index < len(self.required_fields):
                    next_field = self.required_fields[self.current_field_index]
                    response_text = f"✅ تم حفظ **{current_field}**: {user_message}\n\n🔹 يرجى تزويدي بالمعلومة التالية:\n**{next_field}**\n\n💡"
                    self.add_assistant_message(response_text)
                    
                    return ChatResponse(
                        response=response_text,
                        status="success",
                        service_identified=True,
                        service_info=self.service_info,
                        next_field=next_field
                    )
                else:
                    result = await self.create_service_request(
                        self.service_info['service_name'], 
                        self.collected_data
                    )
                    self.state = "completed"
                    
                    data_summary = "\n".join([f"• **{k}**: {v}" for k, v in self.collected_data.items()])
                    response_text = f"✅ تم حفظ **{current_field}**: {user_message}\n\n📋 **ملخص البيانات المجمعة:**\n{data_summary}\n\n{result['message']}"
                    self.add_assistant_message(response_text)
                    
                    return ChatResponse(
                        response=response_text,
                        status="success",
                        service_identified=True,
                        service_info=self.service_info,
                        completed=True
                    )
            
            elif self.state == "completed":
                response_text = "✅ تم إكمال طلبك بنجاح!\n\n🔄 يمكنك بدء طلب جديد بإرسال رسالة جديدة\n📞 أو تتبع طلبك الحالي باستخدام رقم الطلب"
                self.add_assistant_message(response_text)
                
                return ChatResponse(
                    response=response_text,
                    status="completed",
                    completed=True
                )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_response = f"❌ عذراً، حدث خطأ: {str(e)}"
            self.add_assistant_message(error_response)
            
            return ChatResponse(
                response=error_response,
                status="error"
            )