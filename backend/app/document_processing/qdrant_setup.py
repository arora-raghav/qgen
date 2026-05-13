import os
import random
import logging
from typing import Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()
logger = logging.getLogger(__name__)

# Global variables - will be initialized lazily
_client: Optional[QdrantClient] = None
_client_initialized: bool = False
collection_name = os.getenv("COLLECTION_NAME")
model_name = os.getenv("EMBEDDING_MODEL")

if not collection_name:
    logger.warning("⚠️ COLLECTION_NAME environment variable not set")
if not model_name:
    logger.warning("⚠️ EMBEDDING_MODEL environment variable not set")

def get_qdrant_client() -> Optional[QdrantClient]:
    """
    Lazy initialization of Qdrant client.
    Only creates client when enhanced processing is enabled.
    Returns None if disabled or connection fails.
    """
    global _client, _client_initialized
    
    # Check if we already tried to initialize
    if _client_initialized:
        return _client
    
    # Check if enhanced processing is enabled
    try:
        from ..enhanced_config import get_enhanced_config
        config = get_enhanced_config()
        
        if not config.is_enabled:
            logger.info("📝 Qdrant client not needed - enhanced processing disabled")
            _client_initialized = True
            _client = None
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ Could not check enhanced config: {e}")
        _client_initialized = True
        _client = None
        return None
    
    # Try to initialize Qdrant client
    try:
        qdrant_url = os.getenv("QDRANT_URL")
        if not qdrant_url:
            logger.warning("⚠️ QDRANT_URL not configured")
            _client_initialized = True
            _client = None
            return None
            
        logger.info(f"🔌 Initializing Qdrant client: {qdrant_url}")
        _client = QdrantClient(url=qdrant_url)
        
        # Test connection and create collection if needed
        if not _client.collection_exists(collection_name=collection_name):
            logger.info(f"📁 Creating Qdrant collection: {collection_name}")
            _client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
            )
        else:
            logger.info(f"📁 Qdrant collection exists: {collection_name}")
            
        _client_initialized = True
        logger.info("✅ Qdrant client initialized successfully")
        return _client
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Qdrant client: {e}")
        _client_initialized = True
        _client = None
        return None

def retrieve_from_store(question: str, user_id: str, n_points: int = 3) -> list:
    """Retrieve similar documents from Qdrant store."""
    client = get_qdrant_client()
    if not client:
        logger.warning("⚠️ Qdrant client not available for retrieval")
        return []
    try:
        results = client.query_points(
            collection_name=collection_name,
            query=models.Document(text=question, model=model_name),
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="group_id",
                        match=models.MatchValue(
                            value=user_id,
                        ),
                    )
                ]
            ),
            limit=n_points,
        )
        return results.points
    except Exception as e:
        logger.error(f"❌ Failed to retrieve from Qdrant: {e}")
        return []

def remove_data_from_store(user_id: str) -> str:
    """Remove user data from Qdrant store."""
    client = get_qdrant_client()
    if not client:
        logger.warning("⚠️ Qdrant client not available for removal")
        return
        
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="group_id",
                            match=models.MatchValue(
                                value=user_id,
                            ),
                        )
                    ]
                )
            )
        )
        logger.info(f"🗑️ Removed data for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to remove data from Qdrant: {e}")

def rag_pipeline_setup(user_id, documents):
    """Set up RAG pipeline by storing documents in Qdrant."""
    client = get_qdrant_client()
    if not client:
        logger.warning("⚠️ Qdrant client not available for RAG pipeline setup")
        return
        
    try:
        client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=idx,
                    vector=models.Document(text=document["page_content"], model=model_name),
                    payload={"group_id": user_id, "document": document},
                )
                for idx, document in enumerate(documents)
            ],
        )
        logger.info(f"💾 Stored {len(documents)} documents in Qdrant for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Failed to setup RAG pipeline: {e}")

def select_random_chunk(documents):
    """Select a random chunk from documents."""
    if not documents:
        return None, None

    idx = random.randint(0, len(documents) - 1)
    selected_doc = documents[idx]

    content = f"filename:{selected_doc['filename']}\nPage_number:{selected_doc['page_number']}\nPage_Content: {selected_doc['page_content']}\n\n\n"

    return idx, content

# Backward compatibility - create a client property that uses lazy initialization
class _ClientWrapper:
    """Wrapper class to provide backward compatible client access."""
    @property
    def client(self):
        return get_qdrant_client()

# Create module-level client for backward compatibility        
import sys
_wrapper = _ClientWrapper()
sys.modules[__name__].client = _wrapper.client