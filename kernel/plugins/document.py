from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.memory.chroma import ChromaMemoryStore
from semantic_kernel.memory.semantic_text_memory import SemanticTextMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredFileLoader
import semantic_kernel as sk
import json ,logging ,uuid
from pathlib import Path
from config import CHROMA_BASE_PATH
from utils import sanitize_collection_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentPlugin:
    def __init__(self):
        pass

    @kernel_function(
        description="Process and store uploaded documents in semantic memory",
        name="process_document"
    )
    async def process_document(
        self,
        file_path: str,
        namespace: str,
        collection_name: str,
        kernel: sk.Kernel = None
    ) -> str:
        """Process uploaded document and add to semantic memory with persistence"""
        try:
            collection_name = sanitize_collection_name(collection_name)
            
            # Determine file type and load accordingly
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.pdf':
                loader = PyPDFLoader(file_path)
            elif file_extension == '.txt':
                loader = TextLoader(file_path, encoding='utf-8')
            else:
                loader = UnstructuredFileLoader(file_path)
            
            # Load and split document
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            texts = text_splitter.split_documents(documents)
            
            # Get the embedding service and create semantic memory
            embedding_service = kernel.get_service("embedding_service")
            
            # Create persistent memory store
            memory_store = ChromaMemoryStore(persist_directory=CHROMA_BASE_PATH)
            semantic_memory = SemanticTextMemory(
                storage=memory_store,
                embeddings_generator=embedding_service
            )
            
            # Ensure collection exists
            try:
                await memory_store.create_collection(collection_name)
                logger.info(f"Collection {collection_name} created or verified")
            except Exception as collection_error:
                logger.warning(f"Collection creation note: {collection_error}")
            
            # Add texts to semantic memory with unique IDs
            chunks_processed = 0
            for i, text in enumerate(texts):
                try:
                    unique_id = f"{Path(file_path).stem}_{i}_{uuid.uuid4().hex[:8]}"
                    await semantic_memory.save_information(
                        collection=collection_name,
                        text=text.page_content,
                        id=unique_id,
                        description=f"Document chunk {i+1} from {Path(file_path).name}"
                    )
                    chunks_processed += 1
                    logger.info(f"Saved chunk {i+1}/{len(texts)} with ID: {unique_id}")
                except Exception as chunk_error:
                    logger.warning(f"Failed to save chunk {i}: {chunk_error}")
                    continue
            
            # Force persistence by calling persist if available
            try:
                if hasattr(memory_store, 'persist'):
                    await memory_store.persist()
                    logger.info("Memory store persisted successfully")
            except Exception as persist_error:
                logger.warning(f"Persistence warning: {persist_error}")
            
            if chunks_processed > 0:
                return json.dumps({
                    "status": "success",
                    "message": f"تم رفع ومعالجة {chunks_processed} جزء من الملف بنجاح في المجموعة {collection_name}",
                    "chunks_processed": chunks_processed,
                    "total_chunks": len(texts),
                    "file_name": Path(file_path).name,
                    "collection_name": collection_name,
                    "namespace": namespace
                })
            else:
                return json.dumps({
                    "status": "partial_error",
                    "message": "تم معالجة الملف لكن لم يتم حفظ أي أجزاء",
                    "chunks_processed": 0,
                    "total_chunks": len(texts)
                })
                
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return json.dumps({
                "status": "error",
                "message": f"خطأ في معالجة الملف: {str(e)}"
            })