"""Document processing API routes."""

import os
import uuid
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime,timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
import logging
import re

from .document_auth import get_document_user, check_document_limits, DocumentUser
from .models import (
    ProjectCreateRequest, ProjectUpdateRequest, ProjectDetailResponse,
    SchemaGenerateRequest, DatasetGenerateRequest, APIResponse,
    ProjectSummary, DocumentSummary, DatasetSummary,
    SchemaPutRequest
)
from .supabase_client import supabase_service
from fastapi import Body
from .document_processing import generate_dataset_schema, generate_full_dataset, create_chunks, process_document_hybrid
from .background_tasks import get_task_manager, TaskType
from .processing_pipeline import schema_generation_task, dataset_generation_task

# Additional imports for file processing
import tempfile
from pathlib import Path
import PyPDF2
from pptx import Presentation
from docx import Document
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Create router for document processing endpoints
router = APIRouter(prefix="/documents", tags=["Document Processing"])

# In-memory storage for background tasks (in production, use Redis or database)
background_tasks_status = {}

# File validation constants
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg'}
MAX_FILE_SIZE_FREE = 5 * 1024 * 1024  # 5MB for free tier
MAX_FILE_SIZE_PAID = 50 * 1024 * 1024  # 50MB for paid tier
MAX_PAGE_COUNT_FREE = 10
MAX_PAGE_COUNT_PAID = 100

async def validate_file(file: UploadFile, user_tier: str) -> tuple[bool, str, int]:
    """Validate uploaded file and return (is_valid, error_message, page_count)"""
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type {file_ext} not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", 0
    
    # Read file content
    content = await file.read()
    await file.seek(0)  # Reset file pointer for later use
    
    # Check file size
    max_size = MAX_FILE_SIZE_PAID if user_tier in ['paid', 'enterprise'] else MAX_FILE_SIZE_FREE
    if len(content) > max_size:
        size_mb = len(content) / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        return False, f"File size {size_mb:.1f}MB exceeds limit of {max_mb}MB for {user_tier} tier", 0
    
    # Count pages based on file type
    page_count = 0
    try:
        if file_ext == '.pdf':
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            page_count = len(pdf_reader.pages)
        elif file_ext == '.docx':
            # For DOCX, estimate 1 page per 500 words
            doc = Document(io.BytesIO(content))
            word_count = sum(len(paragraph.text.split()) for paragraph in doc.paragraphs)
            page_count = max(1, word_count // 500)
        elif file_ext == '.pptx':
            ppt = Presentation(io.BytesIO(content))
            page_count = len(ppt.slides)
        elif file_ext in ['.png', '.jpg', '.jpeg']:
            page_count = 1  # Image files count as 1 page
            
    except Exception as e:
        logger.warning(f"Could not determine page count for {file.filename}: {e}")
        page_count = 1  # Default to 1 page if we can't determine
    
    # Check page limit
    max_pages = MAX_PAGE_COUNT_PAID if user_tier in ['paid', 'enterprise'] else MAX_PAGE_COUNT_FREE
    if page_count > max_pages:
        return False, f"Document has {page_count} pages, exceeds limit of {max_pages} for {user_tier} tier", page_count
    
    return True, "Valid", page_count

async def upload_to_supabase_storage(file: UploadFile, bucket_name: str, file_path: str, client=None) -> str:
    """Upload file to Supabase Storage and return public URL"""
    try:
        content = await file.read()
        await file.seek(0)  # Reset for any future reads
        
        # Use provided client or fall back to service client
        storage_client = client or supabase_service.get_service_client()
        
        # Upload to Supabase Storage
        response = storage_client.storage.from_(bucket_name).upload(file_path, content)
        
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Upload failed: {response.error}")
        
        # Get public URL (can use any client for public URLs)
        public_url = storage_client.storage.from_(bucket_name).get_public_url(file_path)
        return public_url
        
    except Exception as e:
        logger.error(f"Error uploading to Supabase Storage: {e}")
        raise Exception(f"Failed to upload file: {str(e)}")

def generate_unique_filename(original_filename: str, project_id: str) -> str:
    """Generate unique filename for storage"""
    timestamp = uuid.uuid4().hex[:8]
    file_ext = Path(original_filename).suffix
    safe_name = Path(original_filename).stem[:50]  # Limit filename length
    return f"{project_id}/{timestamp}_{safe_name}{file_ext}"

@router.get("/user/profile")
async def get_user_profile(current_user: DocumentUser = Depends(get_document_user)):
    """Get current user profile and usage information."""
    try:
        client = supabase_service.get_service_client()
        
        # Get user's projects
        projects_response = client.table("projects").select("id").eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        project_ids = [project["id"] for project in projects_response.data] if projects_response.data else []
        
        # Calculate total documents and storage usage
        total_documents = 0
        total_storage_mb = 0.0
        
        if project_ids:
            # Get all documents across user's projects
            documents_response = client.table("documents").select("file_size").in_("project_id", project_ids).is_("deleted_at", "null").execute()
            
            if documents_response.data:
                total_documents = len(documents_response.data)
                # Sum up file sizes (convert bytes to MB)
                total_storage_bytes = sum(doc.get("file_size", 0) for doc in documents_response.data)
                total_storage_mb = round(total_storage_bytes / (1024 * 1024), 2)
        
        return APIResponse(
            success=True,
            data={
                "user_id": current_user.user_id,
                "email": current_user.email,
                "subscription_tier": current_user.subscription_tier,
                "auth_type": "jwt",
                "is_invited": current_user.is_invited,
                "total_documents": total_documents,
                "storage_used_mb": total_storage_mb
            },
            message="User profile retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")

@router.get("/user/limits")
async def check_user_limits_endpoint(
    pages: int = 0,
    mb: float = 0.0,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Check user limits for processing pages and data."""
    try:
        limits_result = await check_document_limits(current_user, pages, mb)
        return APIResponse(
            success=True,
            data=limits_result,
            message="Limits checked successfully"
        )
    except Exception as e:
        logger.error(f"Error checking user limits: {e}")
        raise HTTPException(status_code=500, detail="Failed to check user limits")

@router.get("/projects")
async def list_projects(
    page: int = 1,
    limit: int = 10,
    status_filter: Optional[str] = None,
    current_user: DocumentUser = Depends(get_document_user)
):
    """List user projects with pagination and filtering. (Simplified for RLS compatibility)"""
    try:
        # TEMPORARY: Use service client to be consistent with project creation
        # Since we create projects with service client, we need to list with it too
        client = supabase_service.get_service_client()
        
        query = client.table("projects").select(
            "id, name, description, status, total_pages_processed, processing_time_seconds, created_at, updated_at"
        ).eq("user_id", current_user.user_id).is_("deleted_at", "null")
        
        if status_filter:
            query = query.eq("status", status_filter)
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Execute query with pagination
        response = query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
        
        projects = []
        for project in response.data:
            # FIXED: Get counts separately to avoid complex joins
            documents_count = 0
            datasets_count = 0
            
            try:
                # Simple count queries instead of joins (using same client)
                doc_response = client.table("documents").select("id", count="exact").eq("project_id", project["id"]).execute()
                documents_count = doc_response.count or 0
                
                dataset_response = client.table("datasets").select("id", count="exact").eq("project_id", project["id"]).execute()
                datasets_count = dataset_response.count or 0
            except Exception:
                logger.warning(f"Failed to count documents/datasets for project {project['id']}")
            
            projects.append(ProjectSummary(
                id=project["id"],
                name=project["name"],
                description=project.get("description"),
                status=project["status"],
                documents_count=documents_count,
                datasets_count=datasets_count,
                total_pages_processed=project.get("total_pages_processed", 0),
                processing_time_seconds=project.get("processing_time_seconds", 0),
                created_at=project["created_at"],
                updated_at=project["updated_at"]
            ))
        
        # Get total count for pagination (using same client)
        count_response = client.table("projects").select("id", count="exact").eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        total = count_response.count
        
        pagination = {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
        
        return APIResponse(
            success=True,
            data={"projects": projects, "pagination": pagination},
            message="Projects retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail="Failed to list projects")

@router.post("/projects")
async def create_project(
    request: ProjectCreateRequest,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Create a new project."""
    try:
        # Check if user can create more projects (JWT users have limits)
        # Count current projects using service client for counting
        count_response = supabase_service.get_service_client().table("projects").select("id", count="exact").eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        current_projects = count_response.count
        
        # Check limits based on subscription tier
        max_projects = {"free": 2, "paid": 50, "enterprise": 500}
        limit = max_projects.get(current_user.subscription_tier, 2)
        
        if current_projects >= limit:
            raise HTTPException(
                status_code=403,
                detail=f"Project limit exceeded. {current_user.subscription_tier.title()} tier allows {limit} projects."
            )
        
        project_data = {
            "user_id": current_user.user_id,
            "name": request.name,
            "description": request.description,
            "instruction": request.instruction,
            "status": "created"
        }
        
        # TEMPORARY: Use service client to bypass RLS for now
        # Since RLS is complex with JWT context, use service client temporarily
        client = supabase_service.get_service_client()
        
        logger.info(f"Creating project with data: {project_data}")
        logger.info(f"User ID: {current_user.user_id}")
        
        # Use service client for the insert (bypasses RLS)
        response = client.table("projects").insert(project_data).execute()
        
        # Debug logging
        logger.info(f"Supabase response: {response}")
        logger.info(f"Response data: {response.data}")
        logger.info(f"Response count: {getattr(response, 'count', 'N/A')}")
        
        if hasattr(response, 'error') and response.error:
            logger.error(f"Supabase error: {response.error}")
            raise HTTPException(status_code=500, detail=f"Database error: {response.error}")
        
        if not response.data:
            logger.error(f"No data in response. Full response: {response.__dict__}")
            raise HTTPException(status_code=500, detail="Failed to create project - no data returned")
        
        return APIResponse(
            success=True,
            data=response.data[0],
            message="Project created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail="Failed to create project")

@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Get project details with documents and datasets."""
    try:
        # TEMPORARY: Use service client to be consistent with other endpoints
        # Since we create/list projects with service client, use it for get too
        client = supabase_service.get_service_client()
        
        # Get project
        project_response = client.table("projects").select("*").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").single().execute()
        
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = project_response.data
        
        # Get documents — map DB columns to model fields
        documents_response = client.table("documents").select("*").eq("project_id", project_id).is_("deleted_at", "null").execute()
        documents = []
        for doc in documents_response.data:
            documents.append(DocumentSummary(
                id=doc["id"],
                filename=doc["filename"],
                file_size=doc.get("file_size", 0),
                file_type=doc.get("file_type", ""),
                status=doc.get("status", "uploaded"),
                pages_extracted=doc.get("pages_extracted"),
                pages_processed=doc.get("page_count", 0),
                error_message=doc.get("error_message"),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
            ))
        
        # Get datasets — map DB columns to model fields
        datasets_response = client.table("datasets").select("*").eq("project_id", project_id).execute()
        datasets = []
        for ds in datasets_response.data:
            datasets.append(DatasetSummary(
                id=ds["id"],
                total_records=ds.get("total_records", 0),
                approved_records=ds.get("total_records", 0),
                generation_config=ds.get("schema_used") if isinstance(ds.get("schema_used"), dict) else {"fields": ds.get("schema_used", [])},
                created_at=ds["created_at"],
            ))
        
        return APIResponse(
            success=True,
            data=ProjectDetailResponse(
                id=project["id"],
                name=project["name"],
                description=project.get("description"),
                instruction=project.get("instruction"),
                status=project["status"],
                schema_config=project.get("schema_config"),
                total_pages_processed=project.get("total_pages_processed", 0),
                processing_time_seconds=project.get("processing_time_seconds", 0),
                documents=documents,
                datasets=datasets,
                created_at=project["created_at"],
                updated_at=project["updated_at"]
            ),
            message="Project retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project")

@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Update project details."""
    try:
        # Verify project ownership
        project_response = supabase_service.get_service_client().table("projects").select("id").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").single().execute()
        
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build update data
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if request.name:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.instruction:
            update_data["instruction"] = request.instruction
        
        response = supabase_service.get_service_client().table("projects").update(update_data).eq("id", project_id).execute()
        
        return APIResponse(
            success=True,
            data=response.data[0] if response.data else None,
            message="Project updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail="Failed to update project")

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Soft delete a project."""
    try:
        # Verify project ownership
        logger.info(f"Attempting to delete project {project_id} for user {current_user.user_id}")
        project_response = supabase_service.get_service_client().table("projects").select("id").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").single().execute()
        
        if not project_response.data:
            logger.warning(f"Project {project_id} not found or not owned by user {current_user.user_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Soft delete project
        update_data = {
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Updating project {project_id} with deleted_at timestamp")
        project_update_response = supabase_service.get_service_client().table("projects").update(update_data).eq("id", project_id).execute()
        
        if hasattr(project_update_response, 'error') and project_update_response.error:
            logger.error(f"Error updating project: {project_update_response.error}")
            raise HTTPException(status_code=500, detail=f"Failed to delete project: {project_update_response.error}")
        
        # Soft delete associated documents
        logger.info(f"Updating associated documents for project {project_id}")
        documents_update_response = supabase_service.get_service_client().table("documents").update({"deleted_at": datetime.now(timezone.utc).isoformat()}).eq("project_id", project_id).execute()
        
        if hasattr(documents_update_response, 'error') and documents_update_response.error:
            logger.error(f"Error updating documents: {documents_update_response.error}")
            raise HTTPException(status_code=500, detail=f"Failed to delete associated documents: {documents_update_response.error}")
        
        logger.info(f"Successfully deleted project {project_id}")
        return APIResponse(
            success=True,
            message="Project deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")

@router.post("/projects/{project_id}/documents/upload")
async def upload_documents(
    project_id: str,
    files: List[UploadFile] = File(...),
    current_user: DocumentUser = Depends(get_document_user)
):
    """Upload documents to a project with validation and storage."""
    try:
        # Verify project exists and user has access
        project_response = supabase_service.get_service_client().table("projects").select("*").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = project_response.data[0]
        
        # Check if user can upload more files (JWT users have limits)
        existing_docs = supabase_service.get_service_client().table("documents").select("id", count="exact").eq("project_id", project_id).is_("deleted_at", "null").execute()
        
        max_files_per_project = {"free": 5, "paid": 50, "enterprise": 200}
        limit = max_files_per_project.get(current_user.subscription_tier, 5)
        
        if existing_docs.count + len(files) > limit:
            raise HTTPException(
                status_code=403,
                detail=f"File limit exceeded. {current_user.subscription_tier.title()} tier allows {limit} files per project."
            )
        
        uploaded_files = []
        errors = []
        total_pages = 0
        
        # Validate and upload each file
        for file in files:
            try:
                # Validate file
                is_valid, error_message, page_count = await validate_file(file, current_user.subscription_tier)
                
                if not is_valid:
                    errors.append(f"{file.filename}: {error_message}")
                    continue
                
                # Check total page limit for this upload
                total_pages += page_count
                max_total_pages = MAX_PAGE_COUNT_PAID if current_user.subscription_tier in ['paid', 'enterprise'] else MAX_PAGE_COUNT_FREE
                
                if total_pages > max_total_pages:
                    errors.append(f"{file.filename}: Total pages ({total_pages}) would exceed limit of {max_total_pages}")
                    continue
                
                # Generate unique filename
                unique_filename = generate_unique_filename(file.filename, project_id)
                
                # Upload to Supabase Storage using service client
                storage_url = await upload_to_supabase_storage(file, "documents", unique_filename, supabase_service.get_service_client())
                
                # Save document metadata to database
                doc_data = {
                    "project_id": project_id,
                    "filename": file.filename,
                    "file_path": unique_filename,
                    "file_size": len(await file.read()),
                    "file_type": Path(file.filename).suffix.lower(),
                    "pages_extracted": page_count,  # Correct column name
                    "status": "uploaded"
                }
                
                # Reset file pointer after reading size
                await file.seek(0)
                
                doc_response = supabase_service.get_service_client().table("documents").insert(doc_data).execute()
                
                if doc_response.data:
                    uploaded_files.append({
                        "id": doc_response.data[0]["id"],
                        "filename": file.filename,
                        "size_mb": round(doc_data["file_size"] / (1024 * 1024), 2),
                        "page_count": page_count,
                        "file_type": doc_data["file_type"],
                        "status": "uploaded"
                    })
                else:
                    errors.append(f"{file.filename}: Failed to save to database")
                    
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {e}")
                errors.append(f"{file.filename}: {str(e)}")
        
        # Update project status if files were uploaded
        if uploaded_files:
            supabase_service.get_service_client().table("projects").update({
                "status": "documents_uploaded",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", project_id).execute()
        
        # Prepare response
        success = len(uploaded_files) > 0
        message = f"Uploaded {len(uploaded_files)} files successfully"
        if errors:
            message += f". {len(errors)} files failed: {'; '.join(errors[:3])}"
            if len(errors) > 3:
                message += f" and {len(errors) - 3} more"
        
        return APIResponse(
            success=success,
            data={
                "uploaded_files": uploaded_files,
                "errors": errors,
                "total_uploaded": len(uploaded_files),
                "total_errors": len(errors),
                "total_pages": total_pages
            },
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload documents")

@router.post("/projects/{project_id}/schema/generate")
async def generate_schema(
    project_id: str,
    request: SchemaGenerateRequest,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Generate schema for dataset using AI analysis of uploaded documents."""
    logger.info(f"🎯 Starting schema generation for project {project_id}")
    logger.info(f"👤 User: {current_user.user_id}, Tier: {current_user.subscription_tier}")
    logger.info(f"📝 Request: mode={request.mode}, instruction='{request.instruction[:100] if request.instruction else 'None'}...'")
    logger.info(f"📄 Selected documents: {request.selected_document_ids}")
    
    try:
        # Verify project exists and user has access
        logger.info(f"🔍 Verifying project access for user {current_user.user_id}")
        project_response = supabase_service.get_service_client().table("projects").select("*").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        
        if not project_response.data:
            logger.error(f"❌ Project {project_id} not found for user {current_user.user_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = project_response.data[0]
        logger.info(f"✅ Project found: {project.get('name', 'Unknown')}")
        
        # Check if project has documents
        logger.info(f"🔍 Checking documents for project {project_id}")
        docs_response = supabase_service.get_service_client().table("documents").select("id", count="exact").eq("project_id", project_id).is_("deleted_at", "null").execute()
        
        if docs_response.count == 0:
            logger.error(f"❌ No documents found for project {project_id}")
            raise HTTPException(status_code=400, detail="No documents found. Please upload documents first.")
        
        logger.info(f"✅ Found {docs_response.count} documents in project")
        
        # Start schema generation task
        logger.info(f"🚀 Creating schema generation task")
        task_manager = get_task_manager()
        task_id = task_manager.create_task(
            task_type=TaskType.SCHEMA_GENERATION,
            project_id=project_id,
            user_id=current_user.user_id,
            task_func=schema_generation_task,
            custom_instruction=request.instruction or '',
            mode=request.mode,  # Pass the mode to the task
            selected_document_ids=request.selected_document_ids  # Pass selected documents
        )
        
        logger.info(f"✅ Schema generation task created with ID: {task_id}")
        
        # Update project status
        supabase_service.get_service_client().table("projects").update({
            "status": "processing",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).execute()
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "started",
                "message": "Schema generation started"
            },
            message="Schema generation started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting schema generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to start schema generation")

@router.post("/projects/{project_id}/schema/preview")
async def preview_schema_records(
    project_id: str,
    payload: Dict[str, Any] = Body(...),
    current_user: DocumentUser = Depends(get_document_user)
):
    """Generate a transient sample preview from the current schema and documents."""
    try:
        if not current_user.is_invited:
            raise HTTPException(status_code=403, detail="Access restricted to invited users")

        client = supabase_service.get_service_client()

        # Verify project and fetch schema
        project_resp = client.table("projects").select("schema_config").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").single().execute()
        if not project_resp.data:
            raise HTTPException(status_code=404, detail="Project not found")
        schema_config = (project_resp.data.get("schema_config") or {})
        schema_def = (schema_config.get("schema") or {}).get("generated_schema", [])
        instruction = schema_config.get("instruction") or ""
        if not schema_def:
            raise HTTPException(status_code=400, detail="No schema found. Please generate or define schema first.")

        # Check documents
        docs_resp = client.table("documents").select("*").eq("project_id", project_id).is_("deleted_at", "null").execute()
        documents = docs_resp.data or []
        if len(documents) == 0:
            raise HTTPException(status_code=400, detail="No documents found. Please upload documents first.")

        # Parse and clamp params
        num_records = int(payload.get("num_records", 5))
        num_records = max(1, min(num_records, 10))
        chunk_strategy = (payload.get("chunk_strategy") or "top").lower()
        max_chunk_chars = int(payload.get("max_chunk_chars", 3000))
        max_chunk_chars = max(500, min(max_chunk_chars, 4000))

        # Extract chunks by reusing create_chunks on a temp dir download similar to processing
        used_chunks = []
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download a few files (limit to 5 for speed)
            for doc in documents[:5]:
                try:
                    response = client.storage.from_("documents").download(doc["file_path"])
                    local_path = os.path.join(temp_dir, doc["filename"]) 
                    if response and hasattr(response, 'data') and response.data:
                        with open(local_path, 'wb') as f:
                            f.write(response.data)
                    elif response:
                        with open(local_path, 'wb') as f:
                            f.write(response)
                except Exception:
                    continue
            # Use hybrid processing instead of legacy create_chunks
            all_chunks = []
            for doc in documents[:5]:
                try:
                    response = client.storage.from_("documents").download(doc["file_path"])
                    if response and hasattr(response, 'data') and response.data:
                        file_bytes = response.data
                    elif response:
                        file_bytes = response
                    else:
                        continue
                    
                    # Process using hybrid approach (default to free tier for preview)
                    chunks = await process_document_hybrid(file_bytes, doc["filename"], "free")
                    if chunks:
                        all_chunks.extend(chunks)
                except Exception:
                    continue
            
            chunks = all_chunks
            # Strategy selection
            if chunk_strategy == "random" and len(chunks) > 0:
                import random
                random.shuffle(chunks)
            # Take top N chunks (e.g., 5)
            selected = chunks[:5]
            # Truncate
            acc_chars = 0
            for ch in selected:
                content = ch.get('page_content', '') or ch.get('content', '')
                if not content:
                    continue
                truncated = content[:max_chunk_chars]
                acc_chars += len(truncated)
                used_chunks.append(truncated)

        if len(used_chunks) == 0:
            raise HTTPException(status_code=400, detail="No extractable content from documents")

        # Build system prompt from schema + instruction
        schema_fields_desc = []
        for f in schema_def:
            schema_fields_desc.append(f"- {f.get('key','')}: {f.get('description','')} (type: {f.get('type','string')})")
        schema_description = "\n".join(schema_fields_desc)
        system_prompt = f"""You are a dataset generation expert. Generate structured data records based on the provided document content.\n\nInstruction: {instruction}\n\nRequired Schema:\n{schema_description}\n\nRules:\n- Generate exactly {num_records} records\n- Each record must include ALL schema fields\n- Values should be relevant to the document content\n- Return valid JSON array"""

        user_content = "\n\n---\n\n".join(used_chunks)
        generation_prompt = f"Document Content:\n{user_content}\n\nGenerate {num_records} records following the schema above."

        logger.info(f"🎯 Starting preview generation:")
        logger.info(f"   📊 Target records: {num_records}")
        logger.info(f"   📄 Used chunks: {len(used_chunks)}")
        logger.info(f"   📝 System prompt length: {len(system_prompt)} characters")
        logger.info(f"   📝 Generation prompt length: {len(generation_prompt)} characters")
        logger.info(f"   📝 Generation prompt preview: {generation_prompt[:200]}...")

        # Call generator
        from .document_processing.agents.generation_agent import generation_agent as _gen
        import time as _time
        start = _time.time()
        records = _gen(content=generation_prompt, system_prompt=system_prompt, model="gpt-5-nano")
        elapsed_ms = int((_time.time() - start) * 1000)
        
        logger.info(f"✅ Preview generation completed in {elapsed_ms}ms")
        logger.info(f"📊 Generated {len(records) if isinstance(records, list) else 0} records")
        if not isinstance(records, list):
            records = []

        # Validate
        def is_int(v):
            try:
                return float(v).is_integer()
            except (ValueError, TypeError):
                return False
        def is_number(v):
            try:
                float(v)
                return True
            except (ValueError, TypeError):
                return False
        def is_bool(v):
            return isinstance(v, bool) or str(v).lower() in ["true","false","0","1"]
        def is_date(v):
            from datetime import datetime as _dt
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                try:
                    _dt.strptime(str(v), fmt)
                    return True
                except (ValueError, TypeError):
                    pass
            return False
        def is_datetime(v):
            from datetime import datetime as _dt
            try:
                _dt.fromisoformat(str(v).replace('Z','+00:00'))
                return True
            except (ValueError, TypeError):
                return False

        issues = []
        for idx, rec in enumerate(records):
            for f in schema_def:
                k = f.get('key')
                t = f.get('type','string')
                req = bool(f.get('required', False))
                val = rec.get(k)
                if req and (val is None or val == ""):
                    issues.append({"row": idx+1, "field": k, "type": "required_missing", "message": "Value required"})
                    continue
                if val is None:
                    continue
                vt = str(val)
                if t == 'string':
                    pass
                elif t == 'number' and not is_number(val):
                    issues.append({"row": idx+1, "field": k, "type": "type_mismatch", "message": f"Expected number, got {type(val).__name__} '{vt}'"})
                elif t == 'integer' and not is_int(val):
                    issues.append({"row": idx+1, "field": k, "type": "type_mismatch", "message": f"Expected integer, got '{vt}'"})
                elif t == 'boolean' and not is_bool(val):
                    issues.append({"row": idx+1, "field": k, "type": "type_mismatch", "message": f"Expected boolean, got '{vt}'"})
                elif t == 'date' and not is_date(val):
                    issues.append({"row": idx+1, "field": k, "type": "type_mismatch", "message": f"Expected date, got '{vt}'"})
                elif t == 'datetime' and not is_datetime(val):
                    issues.append({"row": idx+1, "field": k, "type": "type_mismatch", "message": f"Expected datetime, got '{vt}'"})
                elif t == 'enum':
                    allowed = f.get('enum') or f.get('values')
                    if allowed and vt not in allowed:
                        issues.append({"row": idx+1, "field": k, "type": "enum", "message": f"Expected one of {allowed}, got '{vt}'"})

        total = len(records)
        invalid = len(issues)
        valid = total if invalid == 0 else max(0, total - len(set([i['row'] for i in issues])))

        return APIResponse(
            success=True,
            data={
                "records": records[:num_records],
                "validation": {
                    "summary": {"total": total, "valid": valid, "invalid": invalid},
                    "issues": issues
                },
                "used_chunks": {"count": min(5, len(used_chunks)), "chars": sum(len(c) for c in used_chunks)},
                "elapsed_ms": elapsed_ms
            },
            message="Preview generated"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview")

@router.post("/projects/{project_id}/generate")
async def start_dataset_generation(
    project_id: str,
    request: DatasetGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Start dataset generation using the generated schema."""
    logger.info(f"🎯 Starting dataset generation for project {project_id}")
    logger.info(f"📝 Request data: {request.model_dump()}")
    logger.info(f"👤 User: {current_user.user_id}, Tier: {current_user.subscription_tier}")
    logger.info(f"📊 Target records: {request.num_records}")
    
    try:
        # Verify project exists and user has access
        project_response = supabase_service.get_service_client().table("projects").select("*").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        logger.info(f"🗂️ Project query result: {len(project_response.data) if project_response.data else 0} projects found")
        
        if not project_response.data:
            logger.error(f"❌ Project {project_id} not found for user {current_user.user_id}")
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = project_response.data[0]
        logger.info(f"✅ Project found: {project.get('name', 'Unknown')}")
        
        # Check if schema exists
        schema_response = supabase_service.get_service_client().table("projects").select("schema_config").eq("id", project_id).execute()
        logger.info(f"📊 Schema query result: {len(schema_response.data) if schema_response.data else 0} projects found")
        
        if not schema_response.data or not schema_response.data[0].get("schema_config"):
            logger.error(f"❌ No schema found for project {project_id}")
            raise HTTPException(status_code=400, detail="No schema found. Please generate schema first.")
        
        # Validate number of records
        num_records = request.num_records
        max_records = {"free": 50, "paid": 500, "enterprise": 5000}
        limit = max_records.get(current_user.subscription_tier, 50)
        
        if num_records > limit:
            raise HTTPException(
                status_code=403,
                detail=f"Record limit exceeded. {current_user.subscription_tier.title()} tier allows {limit} records."
            )
        
        # Start dataset generation task
        task_manager = get_task_manager()
        task_id = task_manager.create_task(
            task_type=TaskType.DATASET_GENERATION,
            project_id=project_id,
            user_id=current_user.user_id,
            task_func=dataset_generation_task,
            num_records=num_records
        )
        
        # Update project status
        supabase_service.get_service_client().table("projects").update({
            "status": "generating",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).execute()
        
        return APIResponse(
            success=True,
            data={
                "task_id": task_id,
                "status": "started",
                "num_records": num_records,
                "message": "Dataset generation started"
            },
            message=f"Started generating {num_records} records"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting dataset generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to start dataset generation")

# New endpoints for task monitoring and data retrieval

@router.get("/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Get the status of a background task."""
    try:
        task_manager = get_task_manager()
        task_info = task_manager.get_task_status(task_id)
        
        if not task_info:
            # Try to get from database (no user_id filter - processing_jobs table doesn't have user_id column)
            job_response = supabase_service.get_service_client().table("processing_jobs").select("*").eq("id", task_id).execute()
            
            if not job_response.data:
                raise HTTPException(status_code=404, detail="Task not found")
            
            job = job_response.data[0]
            return APIResponse(
                success=True,
                data={
                    "task_id": task_id,
                    "status": job["status"],
                    "progress": job["progress"],
                    "message": job["message"],
                    "result": job["result"],
                    "error": job.get("error_message"),
                    "created_at": job["created_at"],
                    "completed_at": job.get("completed_at")
                },
                message="Task status retrieved"
            )
        
        return APIResponse(
            success=True,
            data=task_info.to_dict(),
            message="Task status retrieved"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")

@router.get("/projects/{project_id}/documents")
async def get_project_documents(
    project_id: str,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Get all documents for a project with their processing status."""
    try:
        # TEMPORARY: Use service client to be consistent with other endpoints
        # Since we create/list projects with service client, use it for get too
        client = supabase_service.get_service_client()
        
        # Verify project access
        project_response = client.table("projects").select("id").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get documents
        docs_response = client.table("documents").select("*").eq("project_id", project_id).is_("deleted_at", "null").execute()
        
        documents = docs_response.data or []
        
        return APIResponse(
            success=True,
            data={
                "documents": documents,
                "total": len(documents)
            },
            message=f"Found {len(documents)} documents"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project documents")

@router.delete("/projects/{project_id}/documents/{document_id}")
async def delete_document(
    project_id: str,
    document_id: str,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Delete a document from a project (soft delete)."""
    try:
        client = supabase_service.get_service_client()
        
        # Verify project access
        project_response = client.table("projects").select("id").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Verify document exists and belongs to this project
        doc_response = client.table("documents").select("*").eq("id", document_id).eq("project_id", project_id).is_("deleted_at", "null").execute()
        
        if not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Soft delete the document
        update_data = {
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        delete_response = client.table("documents").update(update_data).eq("id", document_id).execute()
        
        if not delete_response.data:
            raise HTTPException(status_code=500, detail="Failed to delete document")
        
        return APIResponse(
            success=True,
            message="Document deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")

@router.get("/projects/{project_id}/schema")
async def get_project_schema(
    project_id: str,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Get the generated schema for a project."""
    try:
        # TEMPORARY: Use service client to be consistent with other endpoints
        # Since we create/list projects with service client, use it for get too
        client = supabase_service.get_service_client()
        
        # Get project with schema_config
        project_response = client.table("projects").select("schema_config").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if schema exists in schema_config
        project_data = project_response.data[0]
        schema_config = project_data.get("schema_config")
        
        if not schema_config:
            return APIResponse(
                success=False,
                data=None,
                message="No schema found. Please generate schema first."
            )
        
        return APIResponse(
            success=True,
            data={
                "schema": schema_config.get("schema"),
                "mode": schema_config.get("mode"),  # Add the missing mode field
                "instruction": schema_config.get("instruction"),
                "status": "schema_generated",  # Add status field
                "generated_from_files": schema_config.get("generated_from_files"),
                "generated_at": schema_config.get("generated_at"),
                "created_at": schema_config.get("generated_at"),  # Use generated_at as created_at
                "updated_at": schema_config.get("generated_at")   # Use generated_at as updated_at
            },
            message="Schema retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project schema: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project schema")

# ------------------- Schema Templates -------------------
@router.get("/schema-templates")
async def list_schema_templates(
    category: Optional[str] = None,
    q: Optional[str] = None,
    current_user: DocumentUser = Depends(get_document_user)
):
    """List built-in and user's private schema templates."""
    try:
        if not current_user.is_invited:
            raise HTTPException(status_code=403, detail="Access restricted to invited users")
        client = supabase_service.get_service_client()

        # Builtins
        builtin_query = client.table("schema_templates").select("*").eq("visibility", "builtin")
        if category:
            builtin_query = builtin_query.eq("category", category)
        builtin_templates = builtin_query.execute().data or []

        # User private templates
        user_query = client.table("schema_templates").select("*").eq("visibility", "private").eq("created_by", current_user.user_id)
        if category:
            user_query = user_query.eq("category", category)
        user_templates = user_query.execute().data or []

        def matches_search(t):
            if not q:
                return True
            needle = q.lower()
            return needle in (t.get("name", "").lower()) or needle in (t.get("category", "") or "").lower() or needle in (t.get("description", "") or "").lower()

        builtin_templates = [t for t in builtin_templates if matches_search(t)]
        user_templates = [t for t in user_templates if matches_search(t)]

        return APIResponse(
            success=True,
            data={
                "builtin": builtin_templates,
                "mine": user_templates
            },
            message="Templates retrieved"
        )
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to list templates")

@router.post("/schema-templates")
async def create_schema_template(
    payload: Dict[str, Any] = Body(...),
    current_user: DocumentUser = Depends(get_document_user)
):
    """Save current schema as a private template."""
    try:
        if not current_user.is_invited:
            raise HTTPException(status_code=403, detail="Access restricted to invited users")
        name = (payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="Template name is required")

        schema_json = payload.get("schema_json")
        if not schema_json or not isinstance(schema_json, dict):
            raise HTTPException(status_code=422, detail="schema_json must be an object")

        client = supabase_service.get_service_client()
        insert_data = {
            "name": name,
            "category": payload.get("category"),
            "description": payload.get("description"),
            "tags": payload.get("tags"),
            "schema_json": schema_json,
            "visibility": "private",
            "created_by": current_user.user_id,
        }
        resp = client.table("schema_templates").insert(insert_data).execute()
        return APIResponse(success=True, data=resp.data[0] if resp.data else None, message="Template saved")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create template")

@router.post("/projects/{project_id}/schema/apply-template/{template_id}")
async def apply_schema_template(
    project_id: str,
    template_id: str,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Apply a schema template to the project, replacing current schema."""
    try:
        if not current_user.is_invited:
            raise HTTPException(status_code=403, detail="Access restricted to invited users")
        client = supabase_service.get_service_client()

        # Fetch template (must be builtin or user's private)
        tpl_resp = client.table("schema_templates").select("*").eq("id", template_id).single().execute()
        if not tpl_resp.data:
            raise HTTPException(status_code=404, detail="Template not found")

        tpl = tpl_resp.data
        if tpl.get("visibility") == "private" and tpl.get("created_by") != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to use this template")

        schema_json = tpl.get("schema_json")
        if not schema_json:
            raise HTTPException(status_code=422, detail="Template missing schema_json")

        # Verify project
        proj_resp = client.table("projects").select("schema_config").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").single().execute()
        if not proj_resp.data:
            raise HTTPException(status_code=404, detail="Project not found")

        existing = proj_resp.data.get("schema_config") or {}
        updated_config = {
            "schema": schema_json,
            "instruction": existing.get("instruction"),
            "generated_from_files": existing.get("generated_from_files"),
            "generated_at": existing.get("generated_at"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        client.table("projects").update({
            "schema_config": updated_config,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).execute()

        return APIResponse(success=True, data={"schema": updated_config["schema"]}, message="Template applied")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply template")
@router.put("/projects/{project_id}/schema")
async def update_project_schema(
    project_id: str,
    request: SchemaPutRequest,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Update the project's schema_config.schema with validation."""
    try:
        if not current_user.is_invited:
            raise HTTPException(status_code=403, detail="Access restricted to invited users")
        client = supabase_service.get_service_client()

        # Verify project access
        project_response = client.table("projects").select("schema_config").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").single().execute()
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Validate request.schema.fields
        fields = request.schema.fields
        if not (1 <= len(fields) <= 100):
            raise HTTPException(status_code=422, detail="Schema must have between 1 and 100 fields")

        SUPPORTED_TYPES = {"string", "number", "integer", "boolean", "date", "datetime", "enum"}

        seen = set()
        for f in fields:
            # key validation
            key = f.key.strip()
            if not (1 <= len(key) <= 64):
                raise HTTPException(status_code=422, detail=f"Field key length must be 1-64: {key}")
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
                raise HTTPException(status_code=422, detail=f"Invalid field key: {key}")
            lower = key.lower()
            if lower in seen:
                raise HTTPException(status_code=422, detail=f"Duplicate field key: {key}")
            seen.add(lower)

            # type validation
            if f.type not in SUPPORTED_TYPES:
                raise HTTPException(status_code=422, detail=f"Unsupported type for {key}: {f.type}")

            # description validation
            if f.description is not None and len(f.description) > 200:
                raise HTTPException(status_code=422, detail=f"Description too long for {key}")

        # Build updated schema_config
        existing = project_response.data.get("schema_config") or {}
        new_schema = {
            "generated_schema": [
                {
                    "key": f.key.strip(),
                    "type": f.type,
                    "required": bool(f.required) if f.required is not None else False,
                    "description": (f.description or "").strip()
                }
                for f in fields
            ]
        }

        updated_config = {
            "schema": new_schema,
            "instruction": request.instruction if request.instruction is not None else existing.get("instruction"),
            "generated_from_files": existing.get("generated_from_files"),
            "generated_at": existing.get("generated_at"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        client.table("projects").update({
            "schema_config": updated_config,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", project_id).execute()

        return APIResponse(
            success=True,
            data={"schema": updated_config["schema"]},
            message="Schema updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project schema: {e}")
        raise HTTPException(status_code=500, detail="Failed to update project schema")

@router.get("/projects/{project_id}/dataset")
async def get_project_dataset(
    project_id: str,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: DocumentUser = Depends(get_document_user)
):
    """Get the generated dataset records for a project."""
    try:
        # TEMPORARY: Use service client to be consistent with other endpoints
        # Since we create/list projects with service client, use it for get too
        client = supabase_service.get_service_client()
        
        # Verify project access
        project_response = client.table("projects").select("id").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get dataset
        dataset_response = client.table("datasets").select("*").eq("project_id", project_id).execute()
        
        if not dataset_response.data:
            return APIResponse(
                success=False,
                data=None,
                message="No dataset found. Please generate dataset first."
            )
        
        dataset_data = dataset_response.data[0]
        records = dataset_data.get("data", [])  # Correct field name from database schema
        
        # Apply pagination
        paginated_records = records[offset:offset + limit]
        
        return APIResponse(
            success=True,
            data={
                "records": paginated_records,
                "total_records": len(records),
                "schema": dataset_data.get("schema_used"),  # Correct field name from database schema
                "status": dataset_data.get("status"),
                "offset": offset,
                "limit": limit
            },
            message=f"Retrieved {len(paginated_records)} records"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project dataset: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project dataset")

@router.get("/projects/{project_id}/jobs")
async def get_project_jobs(
    project_id: str,
    current_user: DocumentUser = Depends(get_document_user)
):
    """Get all processing jobs for a project."""
    try:
        # TEMPORARY: Use service client to be consistent with other endpoints
        # Since we create/list projects with service client, use it for get too
        client = supabase_service.get_service_client()
        
        # Verify project access
        project_response = client.table("projects").select("id").eq("id", project_id).eq("user_id", current_user.user_id).is_("deleted_at", "null").execute()
        
        if not project_response.data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get processing jobs (no user_id column in processing_jobs table)
        jobs_response = client.table("processing_jobs").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
        
        jobs = jobs_response.data or []
        
        return APIResponse(
            success=True,
            data={
                "jobs": jobs,
                "total": len(jobs)
            },
            message=f"Found {len(jobs)} processing jobs"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project jobs")

# END OF DOCUMENT_ROUTES.PY
