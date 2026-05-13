"""
Enhanced processing pipeline with Qdrant integration and RAG context assembly.
Only activates when ENABLE_ENHANCED_PROCESSING=true is set.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .enhanced_config import get_enhanced_config, log_processing_mode, log_rag_fallback

logger = logging.getLogger(__name__)

async def enhanced_document_processing(chunks: List[Dict[str, Any]], user_id: str, project_id: str) -> List[Dict[str, Any]]:
    """
    Enhanced document processing with Qdrant storage.
    Only runs if enhanced processing is enabled, otherwise returns chunks unchanged.
    
    Args:
        chunks: List of processed document chunks
        user_id: User identifier for data isolation
        project_id: Project identifier for tracking
        
    Returns:
        List of chunks (same as input if enhanced processing disabled)
    """
    config = get_enhanced_config()
    
    if not config.is_enabled:
        logger.info("📝 Enhanced processing disabled - skipping Qdrant storage")
        return chunks
    
    log_processing_mode("Document Processing")
    
    try:
        # Import Qdrant components only when needed
        from .document_processing.qdrant_setup import rag_pipeline_setup, get_qdrant_client
        
        # Check Qdrant availability
        if not await _check_qdrant_availability():
            log_rag_fallback("Qdrant service unavailable", "Document Processing")
            return chunks
        
        # Store chunks in Qdrant for semantic search
        await _store_chunks_in_qdrant(chunks, user_id, project_id)
        
        logger.info(f"✅ Enhanced processing: Stored {len(chunks)} chunks in Qdrant for user {user_id}")
        return chunks
        
    except Exception as e:
        log_rag_fallback(f"Qdrant storage failed: {str(e)}", "Document Processing")
        return chunks

async def enhanced_context_assembly(base_chunk: Dict[str, Any], user_id: str, n_similar: int = 3) -> Tuple[List[Dict[str, Any]], str]:
    """
    Assemble context using RAG-based semantic similarity.
    Falls back to single chunk if enhanced processing is disabled or fails.
    
    Args:
        base_chunk: The primary chunk to find similar content for
        user_id: User identifier for data isolation
        n_similar: Number of similar chunks to retrieve
        
    Returns:
        Tuple of (context_chunks, assembled_context_text)
    """
    config = get_enhanced_config()
    
    if not config.should_use_rag:
        logger.info("📝 RAG context disabled - using single chunk")
        return [base_chunk], _format_single_chunk_context(base_chunk)
    
    try:
        # Import Qdrant components only when needed
        from .document_processing.qdrant_setup import retrieve_from_store, get_qdrant_client
        
        # Check Qdrant availability
        if not await _check_qdrant_availability():
            log_rag_fallback("Qdrant service unavailable", "Context Assembly")
            return [base_chunk], _format_single_chunk_context(base_chunk)
        
        # Get chunk content for similarity search
        base_content = base_chunk.get('page_content', '') or base_chunk.get('content', '')
        if not base_content:
            logger.warning("⚠️ Base chunk has no content for similarity search")
            return [base_chunk], _format_single_chunk_context(base_chunk)
        
        # Retrieve similar chunks from Qdrant
        similar_results = retrieve_from_store(base_content, user_id, n_similar)
        
        if not similar_results:
            log_rag_fallback("No similar chunks found", "Context Assembly")
            return [base_chunk], _format_single_chunk_context(base_chunk)
        
        # Extract similar chunks from results
        similar_chunks = []
        for result in similar_results:
            if hasattr(result, 'payload') and 'document' in result.payload:
                similar_chunks.append(result.payload['document'])
        
        # Combine with base chunk (avoid duplicates)
        all_chunks = [base_chunk]
        for chunk in similar_chunks:
            if not _is_duplicate_chunk(chunk, all_chunks):
                all_chunks.append(chunk)
        
        # Assemble context text
        context_text = _assemble_context_text(all_chunks)
        
        logger.info(f"🎯 RAG context assembled: {len(all_chunks)} chunks (base + {len(similar_chunks)} similar)")
        return all_chunks, context_text
        
    except Exception as e:
        log_rag_fallback(f"Context assembly failed: {str(e)}", "Context Assembly")
        return [base_chunk], _format_single_chunk_context(base_chunk)

async def _check_qdrant_availability() -> bool:
    """Check if Qdrant service is available and collection exists."""
    try:
        # Import only when checking availability
        from .document_processing.qdrant_setup import get_qdrant_client, collection_name
        
        client = get_qdrant_client()
        if not client:
            return False
        
        # Try to check collection status
        exists = client.collection_exists(collection_name=collection_name)
        return exists
        
    except Exception as e:
        logger.debug(f"Qdrant availability check failed: {e}")
        return False

async def _store_chunks_in_qdrant(chunks: List[Dict[str, Any]], user_id: str, project_id: str):
    """Store chunks in Qdrant with error handling."""
    try:
        # Import only when storing
        from .document_processing.qdrant_setup import rag_pipeline_setup
        
        # Format chunks for Qdrant storage
        formatted_chunks = []
        for chunk in chunks:
            # Ensure chunk has required fields
            formatted_chunk = {
                'filename': chunk.get('filename', 'unknown'),
                'page_number': chunk.get('page_number', 1),
                'page_content': chunk.get('page_content', '') or chunk.get('content', ''),
                'chunk_type': chunk.get('chunk_type', 'unknown'),
                'project_id': project_id  # Add project tracking
            }
            
            # Only add chunks with content
            if formatted_chunk['page_content'].strip():
                formatted_chunks.append(formatted_chunk)
        
        if not formatted_chunks:
            logger.warning("⚠️ No chunks with content found for Qdrant storage")
            return
        
        # Store in Qdrant using the existing setup function
        rag_pipeline_setup(user_id, formatted_chunks)
        
        logger.info(f"💾 Stored {len(formatted_chunks)} chunks in Qdrant for project {project_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to store chunks in Qdrant: {e}")
        raise

def _format_single_chunk_context(chunk: Dict[str, Any]) -> str:
    """Format a single chunk as context text."""
    filename = chunk.get('filename', 'unknown')
    page_number = chunk.get('page_number', 1)
    content = chunk.get('page_content', '') or chunk.get('content', '')
    
    return f"filename:{filename}\nPage_number:{page_number}\nPage_Content: {content}\n\n\n"

def _assemble_context_text(chunks: List[Dict[str, Any]]) -> str:
    """Assemble multiple chunks into formatted context text."""
    context_parts = []
    
    for chunk in chunks:
        filename = chunk.get('filename', 'unknown')
        page_number = chunk.get('page_number', 1)
        content = chunk.get('page_content', '') or chunk.get('content', '')
        
        context_part = f"filename:{filename}\nPage_number:{page_number}\nPage_Content: {content}"
        context_parts.append(context_part)
    
    return "\n\n\n\n".join(context_parts)

def _is_duplicate_chunk(chunk: Dict[str, Any], existing_chunks: List[Dict[str, Any]]) -> bool:
    """Check if a chunk is already in the list (simple duplicate detection)."""
    chunk_content = chunk.get('page_content', '') or chunk.get('content', '')
    if not chunk_content:
        return True  # Skip empty chunks
    
    for existing in existing_chunks:
        existing_content = existing.get('page_content', '') or existing.get('content', '')
        # Simple content-based duplicate detection
        if chunk_content.strip() == existing_content.strip():
            return True
    
    return False