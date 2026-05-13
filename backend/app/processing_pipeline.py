"""
Document processing pipeline functions
"""

import asyncio
import logging
import json
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .supabase_client import supabase_service
from .background_tasks import get_task_manager
from .document_processing.workflow import generate_dataset_schema, generate_full_dataset, generate_full_dataset_async, create_chunks, process_document_hybrid
from .enhanced_processing import enhanced_document_processing
from .enhanced_dataset_generation import generate_full_dataset_enhanced
from .document_processing.cache import chunk_cache
from .document_processing.agents.client_initialization import openai_client

logger = logging.getLogger(__name__)

async def download_file_from_storage(storage_url: str, local_path: str) -> bool:
    """Download file from Supabase Storage to local path"""
    try:
        # Extract file path from storage URL
        # URL format: https://xxx.supabase.co/storage/v1/object/public/documents/path
        url_parts = storage_url.split('/storage/v1/object/public/documents/')
        if len(url_parts) != 2:
            raise ValueError(f"Invalid storage URL format: {storage_url}")
        
        file_path = url_parts[1]
        
        # Download file content
        response = supabase_service.client.storage.from_("documents").download(file_path)
        
        # Write to local file
        with open(local_path, 'wb') as f:
            f.write(response)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to download file from storage: {e}")
        return False

async def schema_generation_task(task_id: str, project_id: str, user_id: str, custom_instruction: str = "", mode: str = "qa", selected_document_ids: List[str] = None) -> Dict[str, Any]:
    """Background task for schema generation"""
    task_manager = get_task_manager()
    
    try:
        # Update progress
        await task_manager.update_task_progress(task_id, 10, "Loading project documents...")
        
        # Get project and documents using service client to avoid RLS issues
        client = supabase_service.get_service_client()
        
        logger.info(f"🔍 Loading project {project_id} for schema generation")
        project_response = client.table("projects").select("*").eq("id", project_id).execute()
        if not project_response.data:
            raise ValueError("Project not found")
        
        project = project_response.data[0]
        logger.info(f"✅ Project loaded: {project.get('name', 'Unknown')}")
        
        # Get documents for this project (with optional filtering)
        if selected_document_ids:
            # Filter to only selected documents
            docs_response = client.table("documents").select("*").eq("project_id", project_id).in_("id", selected_document_ids).is_("deleted_at", "null").execute()
            logger.info(f"🎯 Using selected documents: {selected_document_ids}")
        else:
            # Use all documents in the project
            docs_response = client.table("documents").select("*").eq("project_id", project_id).is_("deleted_at", "null").execute()
            logger.info(f"📂 Using all documents in project")
            
        if not docs_response.data:
            if selected_document_ids:
                raise ValueError("Selected documents not found or access denied")
            else:
                raise ValueError("No documents found in project")
        
        documents = docs_response.data
        await task_manager.update_task_progress(task_id, 20, f"Found {len(documents)} documents")
        
        # Process documents using cache-first approach
        all_chunks = []
        processed_files = []
        
        for i, doc in enumerate(documents):
            progress = 20 + (30 * i // len(documents))
            await task_manager.update_task_progress(task_id, progress, f"Processing {doc['filename']}...")
            
            try:
                # Try to load from cache first
                cached_chunks = chunk_cache.load_chunks(
                    project_id=str(project_id),
                    document_id=str(doc["id"]),
                    filename=doc["filename"],
                    file_size=doc["file_size"]
                )
                
                if cached_chunks:
                    logger.info(f"📂 Using cached chunks for {doc['filename']}: {len(cached_chunks)} chunks")
                    all_chunks.extend(cached_chunks)
                    processed_files.append(doc['filename'])
                else:
                    # Cache miss - process and cache
                    logger.info(f"🔄 Cache miss - processing {doc['filename']}")
                    await task_manager.update_task_progress(
                        task_id, 
                        progress + 5, 
                        f"Processing {doc['filename']} with hybrid approach..."
                    )
                    
                    # Get file from Supabase Storage
                    response = client.storage.from_("documents").download(doc['file_path'])
                    
                    if response and hasattr(response, 'data') and response.data:
                        file_bytes = response.data
                    elif response:
                        # Response might be bytes directly
                        file_bytes = response
                    else:
                        logger.error(f"Empty response for {doc['filename']}")
                        continue
                    
                    # Get user tier for memory threshold
                    user_profile = await supabase_service.get_user_profile(user_id)
                    user_tier = user_profile.get('subscription_tier', 'free') if user_profile else 'free'
                    
                    chunks = await process_document_hybrid(file_bytes, doc['filename'], user_tier)
                    
                    if chunks:
                        all_chunks.extend(chunks)
                        processed_files.append(doc['filename'])
                        logger.info(f"✅ Successfully processed {doc['filename']}: {len(chunks)} chunks")
                        
                        # Cache the processed chunks for future use
                        chunk_cache.save_chunks(
                            project_id=str(project_id),
                            document_id=str(doc["id"]),
                            filename=doc["filename"],
                            file_size=doc["file_size"],
                            chunks=chunks
                        )
                        logger.info(f"💾 Cached chunks for {doc['filename']}: {len(chunks)} chunks")
                    else:
                        logger.warning(f"⚠️ No chunks generated for {doc['filename']}")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {doc['filename']}: {e}")
                continue
        
        if not all_chunks:
            raise ValueError("No content could be extracted from documents")
        
        # Enhanced processing: Store chunks in Qdrant if enabled (for schema generation too)
        all_chunks = await enhanced_document_processing(all_chunks, user_id, project_id)
        
        await task_manager.update_task_progress(task_id, 60, f"Processed {len(processed_files)} files using hybrid approach")
        
        # Combine instruction with project instruction
        full_instruction = project.get('instruction', '')
        if custom_instruction:
            full_instruction = f"{full_instruction}\n\nAdditional Instructions: {custom_instruction}".strip()
        
        if not full_instruction:
            full_instruction = "Extract structured data from the provided documents. Create a schema that captures the key information present in the documents."
        
        await task_manager.update_task_progress(task_id, 70, "Generating schema with AI...")
        
        # Generate schema using AI
        # Prepare content for schema generation
        combined_content = "\n\n".join([chunk.get('page_content', '') or chunk.get('content', '') for chunk in all_chunks[:10]])  # Limit to first 10 chunks
        
        logger.info(f"🔍 Preparing schema generation with {len(all_chunks[:10])} chunks")
        logger.info(f"📝 Combined content length: {len(combined_content)} characters")
        logger.info(f"📝 Full instruction: {full_instruction}")
        logger.info(f"🎯 Schema generation mode: {mode}")
        
        schema_result = generate_dataset_schema(f"{full_instruction}\n\n---\n{combined_content}", mode=mode)
        
        logger.info(f"✅ Schema generation completed successfully")
        logger.info(f"📊 Generated schema with {len(schema_result.generated_schema)} fields")
        
        await task_manager.update_task_progress(task_id, 90, "Saving schema...")
        
        # Save schema to database
        # Convert Pydantic model to dictionary for JSON serialization
        schema_dict = schema_result.model_dump() if hasattr(schema_result, 'model_dump') else schema_result.dict()
        
        # Store schema in project's schema_config field (not in datasets table)
        # datasets table is for actual generated data, not schemas
        project_update = {
            "status": "schema_generated", 
            "schema_config": {
                "mode": mode,  # Store the generation mode
                "schema": schema_dict,
                "instruction": full_instruction,
                "generated_from_files": len(processed_files),
                "selected_document_ids": selected_document_ids if selected_document_ids else [doc["id"] for doc in documents],  # Store document selection
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        client.table("projects").update(project_update).eq("id", project_id).execute()
        
        await task_manager.update_task_progress(task_id, 100, "Schema generation completed")
        
        return {
            "schema": schema_dict,
            "processed_files": processed_files,
            "total_chunks": len(all_chunks),
            "instruction": full_instruction
        }
        
    except Exception as e:
        logger.error(f"Schema generation failed: {e}")
        raise

async def dataset_generation_task(task_id: str, project_id: str, user_id: str, num_records: int = 10) -> Dict[str, Any]:
    """Background task for dataset generation"""
    task_manager = get_task_manager()
    
    try:
        # Update progress
        await task_manager.update_task_progress(task_id, 10, "Loading project and schema...")
        
        # Get project
        project_response = supabase_service.get_service_client().table("projects").select("*").eq("id", project_id).eq("user_id", user_id).is_("deleted_at", "null").execute()
        if not project_response.data:
            raise ValueError("Project not found")
        
        project = project_response.data[0]
        
        # Get schema from project
        schema_config = project.get('schema_config')
        if not schema_config:
            raise ValueError("No schema found. Please generate schema first.")
        
        schema_definition = schema_config.get('schema', {}).get('generated_schema', [])
        
        # Get the selected document IDs that were used for schema generation
        selected_document_ids = schema_config.get('selected_document_ids', [])
        
        await task_manager.update_task_progress(task_id, 20, "Loading documents...")
        
        # Use the same document selection that was used for schema generation
        if selected_document_ids:
            # Filter to only selected documents (same as schema generation)
            docs_response = supabase_service.get_service_client().table("documents").select("*").eq("project_id", project_id).in_("id", selected_document_ids).is_("deleted_at", "null").execute()
            logger.info(f"🎯 Using selected documents for dataset generation: {selected_document_ids}")
        else:
            # Use all documents in the project (fallback for old schemas)
            docs_response = supabase_service.get_service_client().table("documents").select("*").eq("project_id", project_id).is_("deleted_at", "null").execute()
            logger.info(f"📂 Using all documents in project (no selection found in schema)")
            
        if not docs_response.data:
            if selected_document_ids:
                raise ValueError("Selected documents not found or access denied")
            else:
                raise ValueError("No documents found in project")
        
        documents = docs_response.data
        
        # Process documents using cache-first approach
        all_chunks = []
        processed_files = []
        
        for i, doc in enumerate(documents):
            progress = 20 + (30 * i // len(documents))
            await task_manager.update_task_progress(task_id, progress, f"Processing {doc['filename']}...")
            
            try:
                # Try to load from cache first
                cached_chunks = chunk_cache.load_chunks(
                    project_id=str(project_id),
                    document_id=str(doc["id"]),
                    filename=doc["filename"],
                    file_size=doc["file_size"]
                )
                
                if cached_chunks:
                    logger.info(f"📂 Using cached chunks for {doc['filename']}: {len(cached_chunks)} chunks")
                    all_chunks.extend(cached_chunks)
                    processed_files.append(doc['filename'])
                else:
                    # Cache miss - process and cache
                    logger.info(f"🔄 Cache miss - processing {doc['filename']}")
                    await task_manager.update_task_progress(
                        task_id, 
                        progress + 5, 
                        f"Processing {doc['filename']} with hybrid approach..."
                    )
                    
                    # Get file from Supabase Storage
                    response = supabase_service.get_service_client().storage.from_("documents").download(doc['file_path'])
                    
                    if response and hasattr(response, 'data') and response.data:
                        file_bytes = response.data
                    elif response:
                        # Response might be bytes directly
                        file_bytes = response
                    else:
                        logger.error(f"Empty response for {doc['filename']}")
                        continue
                    
                    # Get user tier for memory threshold
                    user_profile = await supabase_service.get_user_profile(user_id)
                    user_tier = user_profile.get('subscription_tier', 'free') if user_profile else 'free'
                    
                    chunks = await process_document_hybrid(file_bytes, doc['filename'], user_tier)
                    
                    if chunks:
                        all_chunks.extend(chunks)
                        processed_files.append(doc['filename'])
                        logger.info(f"✅ Successfully processed {doc['filename']}: {len(chunks)} chunks")
                        
                        # Cache the processed chunks for future use
                        chunk_cache.save_chunks(
                            project_id=str(project_id),
                            document_id=str(doc["id"]),
                            filename=doc["filename"],
                            file_size=doc["file_size"],
                            chunks=chunks
                        )
                        logger.info(f"💾 Cached chunks for {doc['filename']}: {len(chunks)} chunks")
                    else:
                        logger.warning(f"⚠️ No chunks generated for {doc['filename']}")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {doc['filename']}: {e}")
                continue
        
        if not all_chunks:
            raise ValueError("No content could be extracted from documents")
        
        # Enhanced processing: Store chunks in Qdrant if enabled
        logger.info(f"🔧 Processing {len(all_chunks)} chunks with enhanced processing")
        all_chunks = await enhanced_document_processing(all_chunks, user_id, project_id)
        logger.info(f"✅ Enhanced processing completed, {len(all_chunks)} chunks ready")
        
        await task_manager.update_task_progress(task_id, 50, f"Generating {num_records} records from {len(processed_files)} processed files...")
        
        logger.info(f"🎯 Starting dataset generation:")
        logger.info(f"   📊 Target records: {num_records}")
        logger.info(f"   📄 Available chunks: {len(all_chunks)}")
        logger.info(f"   🏗️ Schema fields: {len(schema_definition)}")
        logger.info(f"   👤 User ID: {user_id}")
        
        # Generate dataset using enhanced generation if enabled, otherwise use standard async
        dataset_records = await generate_full_dataset_enhanced(
            chunks=all_chunks,
            schema=schema_definition,
            num_records=num_records,
            user_id=user_id,
            task_id=task_id  # Pass task_id for progress updates
        )
        
        logger.info(f"✅ Dataset generation completed successfully")
        logger.info(f"📊 Generated {len(dataset_records)} records")
        
        await task_manager.update_task_progress(task_id, 90, "Saving dataset...")
        
        # Use service client for consistency 
        client = supabase_service.get_service_client()
        
        # Check if dataset already exists for this project
        existing_dataset = client.table("datasets").select("id").eq("project_id", project_id).execute()
        
        dataset_data = {
            "project_id": project_id,
            "data": dataset_records,  # Correct field name from schema
            "schema_used": schema_definition,  # Store the schema that was used
            "total_records": len(dataset_records),
            "approved_records": len(dataset_records),  # Default all to approved
            "generation_config": {
                "num_records_requested": num_records,
                "chunks_processed": len(all_chunks),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        if existing_dataset.data:
            # Update existing dataset
            dataset_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            client.table("datasets").update(dataset_data).eq("project_id", project_id).execute()
            logger.info(f"Updated existing dataset for project {project_id}")
        else:
            # Create new dataset
            client.table("datasets").insert(dataset_data).execute()
            logger.info(f"Created new dataset for project {project_id}")
        
        # Update project status
        client.table("projects").update({
            "status": "completed",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).execute()
        
        await task_manager.update_task_progress(task_id, 100, "Dataset generation completed")
        
        return {
            "total_records": len(dataset_records),
            "records": dataset_records[:5],  # Return first 5 records as preview
            "schema": schema_definition
        }
        
    except Exception as e:
        logger.error(f"Dataset generation failed: {e}")
        raise

async def document_processing_task(task_id: str, project_id: str, user_id: str, document_ids: List[str]) -> Dict[str, Any]:
    """Background task for processing individual documents using hybrid approach"""
    task_manager = get_task_manager()
    
    try:
        await task_manager.update_task_progress(task_id, 10, "Starting document processing...")
        
        processed_documents = []
        total_docs = len(document_ids)
        
        for i, doc_id in enumerate(document_ids):
            progress = 10 + (80 * i // total_docs)
            
            # Get document
            doc_response = supabase_service.get_service_client().table("documents").select("*").eq("id", doc_id).execute()
            if not doc_response.data:
                continue
            
            doc = doc_response.data[0]
            await task_manager.update_task_progress(task_id, progress, f"Processing {doc['filename']}...")
            
            # Process document using hybrid approach
            try:
                # Get file from Supabase Storage
                logger.info(f"Processing file: {doc['file_path']}")
                response = supabase_service.get_service_client().storage.from_("documents").download(doc['file_path'])
                
                if response and hasattr(response, 'data') and response.data:
                    file_bytes = response.data
                elif response:
                    # Response might be bytes directly
                    file_bytes = response
                else:
                    logger.error(f"Empty response for {doc['filename']}")
                    continue
                
                # Get user tier for memory threshold
                user_profile = await supabase_service.get_user_profile(user_id)
                user_tier = user_profile.get('subscription_tier', 'free') if user_profile else 'free'
                
                # Process document using hybrid approach
                await task_manager.update_task_progress(
                    task_id, 
                    progress + 5, 
                    f"Processing {doc['filename']} with hybrid approach..."
                )
                
                chunks = await process_document_hybrid(file_bytes, doc['filename'], user_tier)
                
                if chunks:
                    # Update document status
                    supabase_service.client.table("documents").update({
                        "status": "processed",
                        "metadata": {"chunks_extracted": len(chunks)},
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", doc_id).execute()
                    
                    processed_documents.append({
                        "document_id": doc_id,
                        "filename": doc['filename'],
                        "chunks_extracted": len(chunks)
                    })
                    
                    logger.info(f"✅ Successfully processed {doc['filename']}: {len(chunks)} chunks")
                else:
                    logger.warning(f"⚠️ No chunks generated for {doc['filename']}")
                    
                    # Update document status to error
                    supabase_service.client.table("documents").update({
                        "status": "error",
                        "metadata": {"error": "No chunks generated"},
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", doc_id).execute()
                
            except Exception as e:
                logger.error(f"❌ Failed to process document {doc['filename']}: {e}")
                
                # Update document status to error
                supabase_service.client.table("documents").update({
                    "status": "error",
                    "metadata": {"error": str(e)},
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", doc_id).execute()
        
        await task_manager.update_task_progress(task_id, 100, f"Processed {len(processed_documents)} documents")
        
        return {
            "processed_documents": processed_documents,
            "total_processed": len(processed_documents),
            "total_requested": total_docs
        }
        
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise
