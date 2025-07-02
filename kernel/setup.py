import logging
import semantic_kernel as sk
from semantic_kernel.connectors.ai.ollama import OllamaTextCompletion
from semantic_kernel.connectors.ai.hugging_face import HuggingFaceTextEmbedding
from semantic_kernel.connectors.memory.chroma import ChromaMemoryStore
from semantic_kernel.memory.semantic_text_memory import SemanticTextMemory
from semantic_kernel.core_plugins.text_memory_plugin import TextMemoryPlugin

from config import CHROMA_BASE_PATH
from .plugins.service_identification import ServiceIdentificationPlugin
from .plugins.validation import ValidationPlugin
from .plugins.database import DatabasePlugin
from .plugins.conversation import ConversationPlugin
from .plugins.document import DocumentPlugin

logger = logging.getLogger(__name__)

class SemanticKernelConfig:
    def __init__(self):
        self.kernel = sk.Kernel()
        
        self.text_completion_service = OllamaTextCompletion(
            ai_model_id="granite3.3",
            service_id="text_completion"
        )
        self.kernel.add_service(self.text_completion_service)

        self.embedding_service = HuggingFaceTextEmbedding(
            ai_model_id="all-MiniLM-L6-v2",
            service_id="embedding_service"
        )
        self.kernel.add_service(self.embedding_service)
        
        # Setup Memory
        self.setup_memory()
        
        # Register Plugins
        self.register_plugins()
    
    def setup_memory(self):
        """Setup semantic memory with persistent Chroma"""
        try:
            self.memory_store = ChromaMemoryStore(
                persist_directory=CHROMA_BASE_PATH
            )
            
            self.semantic_memory = SemanticTextMemory(
                storage=self.memory_store,
                embeddings_generator=self.embedding_service
            )
            
            memory_plugin = TextMemoryPlugin(memory=self.semantic_memory)
            self.kernel.add_plugin(memory_plugin, "memory")
            
            logger.info(f"Persistent semantic memory setup completed at: {CHROMA_BASE_PATH}")
            
        except Exception as e:
            logger.error(f"Error setting up memory: {e}")
            self.semantic_memory = None

    def register_plugins(self):
        """Register all plugins with the kernel"""
        self.kernel.add_plugin(ServiceIdentificationPlugin(), "service_id")
        self.kernel.add_plugin(ValidationPlugin(), "validation")
        self.kernel.add_plugin(DatabasePlugin(), "database")
        self.kernel.add_plugin(ConversationPlugin(), "conversation")
        self.kernel.add_plugin(DocumentPlugin(), "document")