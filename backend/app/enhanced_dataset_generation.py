"""
Enhanced dataset generation workflow with RAG context and evolution features.
"""

import asyncio
import json
import logging
import random
import time
from typing import List, Dict, Any, Optional

from .enhanced_config import get_enhanced_config, log_processing_mode, log_rag_fallback
from .enhanced_processing import enhanced_context_assembly
from .document_processing.agents.generation_agent import generation_agent, generation_agent_async
from .document_processing.agents.evolution_agent.evolver import evolve_dataset

logger = logging.getLogger(__name__)

async def generate_full_dataset_enhanced(
    chunks: List[Dict[str, Any]], 
    schema: List[Dict[str, Any]], 
    num_records: int, 
    user_id: str,
    task_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Enhanced dataset generation with RAG context assembly and evolution.
    Falls back to standard generation if enhanced features are disabled or fail.
    
    Args:
        chunks: List of document chunks with content
        schema: Schema definition with field specifications  
        num_records: Number of records to generate
        user_id: User identifier for RAG context isolation
        task_id: Optional task ID for progress updates
        
    Returns:
        List of generated dataset records
    """
    config = get_enhanced_config()
    
    if not config.is_enabled:
        # Fall back to existing async generation
        from .document_processing.workflow import generate_full_dataset_async
        logger.info("📝 Enhanced generation disabled - using standard workflow")
        return await generate_full_dataset_async(chunks, schema, num_records, task_id)
    
    log_processing_mode("Dataset Generation")
    
    try:
        return await _generate_with_rag_and_evolution(chunks, schema, num_records, user_id, task_id)
    except Exception as e:
        log_rag_fallback(f"Enhanced generation failed: {str(e)}", "Dataset Generation")
        # Fall back to standard generation
        from .document_processing.workflow import generate_full_dataset_async
        logger.info("🔽 Falling back to standard dataset generation")
        return await generate_full_dataset_async(chunks, schema, num_records, task_id)

async def _generate_with_rag_and_evolution(
    chunks: List[Dict[str, Any]], 
    schema: List[Dict[str, Any]], 
    num_records: int, 
    user_id: str,
    task_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Enhanced generation with RAG context and evolution."""
    config = get_enhanced_config()
    
    logger.info(f"🎯 Enhanced dataset generation starting:")
    logger.info(f"   📊 Target records: {num_records}")
    logger.info(f"   📄 Available chunks: {len(chunks)}")
    logger.info(f"   🏗️ Schema fields: {len(schema)}")
    logger.info(f"   👤 User ID: {user_id}")
    logger.info(f"   🔧 Task ID: {task_id}")
    logger.info(f"   Evolution depth: {config.evolution_depth}")
    
    if not chunks or not schema:
        logger.error("No chunks or schema provided for dataset generation")
        return []
    
    # Create schema description 
    schema_fields_desc = []
    for field in schema:
        schema_fields_desc.append(f"- {field.get('key','')}: {field.get('description','')} (type: {field.get('type','string')})")
    schema_description = "\\n".join(schema_fields_desc)
    
    # System prompt for generation
    system_prompt = f"""You are a dataset generation expert. Generate structured data records based on the provided document content.

**Required Schema:**
{schema_description}

**Instructions:**
1. Analyze the provided document content carefully
2. Generate realistic records that follow the exact schema above
3. Each record must include ALL schema fields
4. Values should be relevant to the document content
5. Ensure data quality and consistency
6. Return valid JSON array format

**Output Format:**
Return a JSON array where each object represents one record with all schema fields."""

    dataset = []
    
    # Process chunks using RAG-enhanced approach
    if num_records >= len(chunks):
        # Standard parallel processing with RAG context
        dataset = await _parallel_generation_with_rag(chunks, schema, num_records, user_id, system_prompt)
    else:
        # Smart selection with RAG context
        dataset = await _smart_selection_with_rag(chunks, schema, num_records, user_id, system_prompt)
    
    logger.info(f"📊 Base generation completed: {len(dataset)} records")
    
    # Apply dataset evolution if enabled
    if config.should_evolve_datasets and dataset:
        dataset = await _apply_dataset_evolution(dataset, schema, config.evolution_depth)
    
    # Ensure exact record count
    dataset = dataset[:num_records] if len(dataset) > num_records else dataset
    
    logger.info(f"✅ Enhanced dataset generation completed: {len(dataset)} records")
    return dataset

async def _parallel_generation_with_rag(
    chunks: List[Dict[str, Any]], 
    schema: List[Dict[str, Any]], 
    num_records: int, 
    user_id: str, 
    system_prompt: str
) -> List[Dict[str, Any]]:
    """Parallel generation using RAG context assembly."""
    
    # Distribute records across chunks
    base_records_per_chunk = num_records // len(chunks)
    remainder = num_records % len(chunks)
    
    chunk_record_counts = []
    for i in range(len(chunks)):
        records_for_chunk = base_records_per_chunk + (1 if i < remainder else 0)
        chunk_record_counts.append(records_for_chunk)
    
    logger.info(f"📈 Parallel RAG generation: {chunk_record_counts} (total: {sum(chunk_record_counts)} records)")
    
    async def process_chunk_with_rag(i: int, chunk: Dict[str, Any], batch_records: int) -> List[Dict[str, Any]]:
        if batch_records <= 0:
            return []
            
        try:
            # Assemble RAG context 
            context_chunks, context_text = await enhanced_context_assembly(chunk, user_id, n_similar=3)
            
            # Generate records using enhanced context
            generation_prompt = f"""Document Content:
{context_text}

Generate {batch_records} records based on this content following the schema above."""
            
            logger.info(f"🧠 Generating {batch_records} records with RAG context ({len(context_chunks)} chunks)")
            
            batch_result = await generation_agent_async(
                content=generation_prompt,
                system_prompt=system_prompt,
                model="gpt-5-nano"
            )
            
            # Parse result
            if isinstance(batch_result, str):
                try:
                    batch_records_data = json.loads(batch_result)
                    if isinstance(batch_records_data, list):
                        return batch_records_data[:batch_records]
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing failed: {e}")
            elif isinstance(batch_result, list):
                return batch_result[:batch_records]
                
            return []
            
        except Exception as e:
            logger.error(f"RAG generation failed for chunk {i+1}: {e}")
            return []
    
    # Execute parallel processing
    tasks = []
    for i, chunk in enumerate(chunks):
        batch_records = chunk_record_counts[i] 
        task = process_chunk_with_rag(i, chunk, batch_records)
        tasks.append(task)
    
    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    dataset = []
    for i, result in enumerate(chunk_results):
        if isinstance(result, Exception):
            logger.error(f"Chunk {i+1} failed: {result}")
        elif isinstance(result, list):
            dataset.extend(result)
    
    return dataset

async def _smart_selection_with_rag(
    chunks: List[Dict[str, Any]], 
    schema: List[Dict[str, Any]], 
    num_records: int, 
    user_id: str, 
    system_prompt: str
) -> List[Dict[str, Any]]:
    """Smart chunk selection with RAG context for quality-focused generation."""
    
    # Select chunks with most content
    chunks_with_size = []
    for i, chunk in enumerate(chunks):
        content = chunk.get('page_content', '') or chunk.get('content', '')
        content_length = len(content.strip()) if content else 0
        chunks_with_size.append((i, chunk, content_length))
    
    # Sort by content length and select top chunks
    chunks_with_size.sort(key=lambda x: x[2], reverse=True)
    selected_chunks = chunks_with_size[:num_records]
    
    logger.info(f"🧠 Smart selection with RAG: {len(selected_chunks)} best chunks")
    
    dataset = []
    for i, (orig_idx, chunk, length) in enumerate(selected_chunks):
        try:
            # Assemble RAG context
            context_chunks, context_text = await enhanced_context_assembly(chunk, user_id, n_similar=3)
            
            # Generate single record with rich context
            generation_prompt = f"""Document Content:
{context_text}

Generate 1 high-quality record based on this content following the schema above."""
            
            logger.info(f"🎯 Generating record {i+1}/{len(selected_chunks)} with RAG context ({len(context_chunks)} chunks)")
            
            batch_result = await generation_agent_async(
                content=generation_prompt,
                system_prompt=system_prompt, 
                model="gpt-5-nano"
            )
            
            # Parse and add to dataset
            if isinstance(batch_result, str):
                try:
                    batch_records_data = json.loads(batch_result)
                    if isinstance(batch_records_data, list) and batch_records_data:
                        dataset.append(batch_records_data[0])
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing failed: {e}")
            elif isinstance(batch_result, list) and batch_result:
                dataset.append(batch_result[0])
                
        except Exception as e:
            logger.error(f"Smart generation failed for chunk {i+1}: {e}")
            continue
    
    return dataset

async def _apply_dataset_evolution(
    dataset: List[Dict[str, Any]], 
    schema: List[Dict[str, Any]], 
    evolution_depth: int
) -> List[Dict[str, Any]]:
    """Apply dataset evolution for enhanced quality and diversity."""
    
    if not dataset or evolution_depth <= 0:
        return dataset
    
    logger.info(f"🧬 Applying dataset evolution: {evolution_depth} rounds on {len(dataset)} records")
    
    try:
        evolved_records = []
        
        for record in dataset:
            try:
                # Apply evolution to each record
                evolved_record = await asyncio.to_thread(evolve_dataset, [record])
                
                if evolved_record and isinstance(evolved_record, list):
                    evolved_records.extend(evolved_record)
                else:
                    # Keep original if evolution fails
                    evolved_records.append(record)
                    
            except Exception as e:
                logger.warning(f"Evolution failed for record, keeping original: {e}")
                evolved_records.append(record)
        
        # Combine original and evolved records
        all_records = dataset + evolved_records
        
        logger.info(f"🎯 Evolution completed: {len(dataset)} → {len(all_records)} total records")
        return all_records
        
    except Exception as e:
        logger.error(f"Dataset evolution failed: {e}")
        return dataset

# Synchronous wrapper for backwards compatibility
def generate_full_dataset_enhanced_sync(
    chunks: List[Dict[str, Any]], 
    schema: List[Dict[str, Any]], 
    num_records: int, 
    user_id: str,
    task_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for enhanced dataset generation."""
    try:
        return asyncio.run(generate_full_dataset_enhanced(chunks, schema, num_records, user_id, task_id))
    except Exception as e:
        logger.error(f"Enhanced sync generation failed: {e}")
        # Fall back to existing sync generation
        from .document_processing.workflow import generate_full_dataset
        return generate_full_dataset(chunks, schema, num_records, task_id)