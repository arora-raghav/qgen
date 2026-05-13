import os
import json
import hashlib
import time
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ChunkCache:
    """File system cache for processed document chunks."""
    
    def __init__(self, cache_dir: str = "/tmp/cache", max_size_gb: float = 1.0, ttl_days: int = 7):
        self.cache_dir = Path(cache_dir)
        self.chunks_dir = self.cache_dir / "chunks"
        self.metadata_dir = self.cache_dir / "metadata"
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)  # Convert GB to bytes
        self.ttl_seconds = ttl_days * 24 * 60 * 60  # Convert days to seconds
        
        # Create cache directories
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🗂️ ChunkCache initialized: {self.cache_dir}, max_size: {max_size_gb}GB, ttl: {ttl_days}days")
    
    def _get_document_hash(self, project_id: str, document_id: str, filename: str, file_size: int) -> str:
        """Generate a unique hash for the document."""
        content = f"{project_id}_{document_id}_{filename}_{file_size}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cache_path(self, project_id: str, document_id: str, doc_hash: str) -> Path:
        """Get the cache file path for a document."""
        project_dir = self.chunks_dir / f"project_{project_id}"
        project_dir.mkdir(exist_ok=True)
        return project_dir / f"doc_{document_id}_{doc_hash}.json"
    
    def _get_metadata_path(self, project_id: str) -> Path:
        """Get the metadata file path for a project."""
        project_dir = self.metadata_dir / f"project_{project_id}"
        project_dir.mkdir(exist_ok=True)
        return project_dir / "cache_index.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired."""
        if not cache_path.exists():
            return False
        
        # Check TTL
        file_age = time.time() - cache_path.stat().st_mtime
        if file_age > self.ttl_seconds:
            logger.info(f"⏰ Cache expired: {cache_path} (age: {file_age/3600:.1f}h)")
            return False
        
        return True
    
    def _get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total_size = 0
        for file_path in self.chunks_dir.rglob("*.json"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def _cleanup_old_files(self):
        """Remove files older than TTL."""
        current_time = time.time()
        removed_count = 0
        
        for file_path in self.chunks_dir.rglob("*.json"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > self.ttl_seconds:
                    try:
                        file_path.unlink()
                        removed_count += 1
                        logger.info(f"🗑️ Removed expired cache: {file_path}")
                    except Exception as e:
                        logger.error(f"❌ Failed to remove expired cache {file_path}: {e}")
        
        if removed_count > 0:
            logger.info(f"🧹 Cleanup completed: removed {removed_count} expired files")
    
    def _enforce_size_limit(self):
        """Remove oldest files if cache exceeds size limit."""
        current_size = self._get_cache_size()
        if current_size <= self.max_size_bytes:
            return
        
        logger.info(f"📏 Cache size limit exceeded: {current_size/1024/1024:.1f}MB > {self.max_size_bytes/1024/1024:.1f}MB")
        
        # Get all cache files with their modification times
        cache_files = []
        for file_path in self.chunks_dir.rglob("*.json"):
            if file_path.is_file():
                cache_files.append((file_path, file_path.stat().st_mtime))
        
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x[1])
        
        # Remove oldest files until under limit
        removed_size = 0
        for file_path, _ in cache_files:
            if current_size - removed_size <= self.max_size_bytes:
                break
            
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                removed_size += file_size
                logger.info(f"🗑️ Removed old cache: {file_path} ({file_size/1024:.1f}KB)")
            except Exception as e:
                logger.error(f"❌ Failed to remove old cache {file_path}: {e}")
        
        logger.info(f"🧹 Size limit enforcement completed: removed {removed_size/1024/1024:.1f}MB")
    
    def save_chunks(self, project_id: str, document_id: str, filename: str, file_size: int, chunks: List[Dict]) -> bool:
        """Save processed chunks to cache."""
        try:
            doc_hash = self._get_document_hash(project_id, document_id, filename, file_size)
            cache_path = self._get_cache_path(project_id, document_id, doc_hash)
            
            # Prepare cache data
            cache_data = {
                "project_id": project_id,
                "document_id": document_id,
                "filename": filename,
                "file_size": file_size,
                "doc_hash": doc_hash,
                "chunks": chunks,
                "created_at": datetime.now().isoformat(),
                "chunk_count": len(chunks)
            }
            
            # Save to cache file
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # Update metadata
            self._update_metadata(project_id, document_id, doc_hash, cache_path)
            
            # Cleanup and enforce limits
            self._cleanup_old_files()
            self._enforce_size_limit()
            
            logger.info(f"💾 Cached chunks: {len(chunks)} chunks for {filename} -> {cache_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save chunks to cache: {e}")
            return False
    
    def load_chunks(self, project_id: str, document_id: str, filename: str, file_size: int) -> Optional[List[Dict]]:
        """Load processed chunks from cache."""
        try:
            doc_hash = self._get_document_hash(project_id, document_id, filename, file_size)
            cache_path = self._get_cache_path(project_id, document_id, doc_hash)
            
            # Check if cache is valid
            if not self._is_cache_valid(cache_path):
                logger.info(f"⏰ Cache invalid or expired: {cache_path}")
                return None
            
            # Load cache data
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Validate cache data
            if not self._validate_cache_data(cache_data, project_id, document_id, filename, file_size):
                logger.warning(f"⚠️ Cache data validation failed: {cache_path}")
                return None
            
            chunks = cache_data.get("chunks", [])
            logger.info(f"📂 Loaded from cache: {len(chunks)} chunks for {filename}")
            return chunks
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Corrupted cache file: {cache_path} - {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load chunks from cache: {e}")
            return None
    
    def _validate_cache_data(self, cache_data: Dict, project_id: str, document_id: str, filename: str, file_size: int) -> bool:
        """Validate cache data integrity."""
        try:
            # Check required fields
            if not all(key in cache_data for key in ["project_id", "document_id", "filename", "file_size", "chunks"]):
                return False
            
            # Check data consistency
            if (cache_data["project_id"] != project_id or 
                cache_data["document_id"] != document_id or 
                cache_data["filename"] != filename or 
                cache_data["file_size"] != file_size):
                return False
            
            # Check chunks structure
            chunks = cache_data.get("chunks", [])
            if not isinstance(chunks, list):
                return False
            
            # Validate chunk structure
            for chunk in chunks:
                if not isinstance(chunk, dict) or "page_content" not in chunk:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache validation error: {e}")
            return False
    
    def _update_metadata(self, project_id: str, document_id: str, doc_hash: str, cache_path: Path):
        """Update project metadata with cache information."""
        try:
            metadata_path = self._get_metadata_path(project_id)
            
            # Load existing metadata
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # Update metadata
            if "documents" not in metadata:
                metadata["documents"] = {}
            
            metadata["documents"][document_id] = {
                "doc_hash": doc_hash,
                "cache_path": str(cache_path),
                "last_updated": datetime.now().isoformat()
            }
            
            # Save metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"❌ Failed to update metadata: {e}")
    
    def clear_project_cache(self, project_id: str):
        """Clear all cache for a project."""
        try:
            project_chunks_dir = self.chunks_dir / f"project_{project_id}"
            project_metadata_dir = self.metadata_dir / f"project_{project_id}"
            
            if project_chunks_dir.exists():
                shutil.rmtree(project_chunks_dir)
                logger.info(f"🗑️ Cleared project cache: {project_chunks_dir}")
            
            if project_metadata_dir.exists():
                shutil.rmtree(project_metadata_dir)
                logger.info(f"🗑️ Cleared project metadata: {project_metadata_dir}")
                
        except Exception as e:
            logger.error(f"❌ Failed to clear project cache: {e}")
    
    def clear_document_cache(self, project_id: str, document_id: str):
        """Clear cache for a specific document."""
        try:
            project_chunks_dir = self.chunks_dir / f"project_{project_id}"
            if not project_chunks_dir.exists():
                return
            
            # Find and remove document cache files
            for cache_file in project_chunks_dir.glob(f"doc_{document_id}_*.json"):
                cache_file.unlink()
                logger.info(f"🗑️ Cleared document cache: {cache_file}")
            
            # Update metadata
            metadata_path = self._get_metadata_path(project_id)
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                if "documents" in metadata and document_id in metadata["documents"]:
                    del metadata["documents"][document_id]
                    
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                        
        except Exception as e:
            logger.error(f"❌ Failed to clear document cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            total_files = 0
            total_size = 0
            project_count = 0
            
            for project_dir in self.chunks_dir.iterdir():
                if project_dir.is_dir() and project_dir.name.startswith("project_"):
                    project_count += 1
                    for cache_file in project_dir.glob("*.json"):
                        if cache_file.is_file():
                            total_files += 1
                            total_size += cache_file.stat().st_size
            
            return {
                "total_files": total_files,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "project_count": project_count,
                "cache_dir": str(self.cache_dir),
                "max_size_gb": self.max_size_bytes / 1024 / 1024 / 1024,
                "ttl_days": self.ttl_seconds / 24 / 60 / 60
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return {}

# Global cache instance
chunk_cache = ChunkCache()
