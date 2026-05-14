"""
Local SQLite + filesystem replacement for Supabase.

Implements the same fluent query-builder interface used throughout the app
so that document_routes.py / processing_pipeline.py / background_tasks.py
need only minimal patches (import path changes).

Table layout (auto-created on first use):
  projects, documents, datasets, schema_templates, processing_jobs
"""

import sqlite3
import json
import uuid
import os
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Storage root                                                                  #
# --------------------------------------------------------------------------- #
_DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data"
_BASE_DIR = Path(os.getenv("QGEN_DATA_DIR", str(_DEFAULT_DATA))).resolve()
_DB_PATH   = _BASE_DIR / "qgen.db"
_FILES_DIR = _BASE_DIR / "files"


def _ensure_dirs():
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    _FILES_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# DB bootstrap                                                                  #
# --------------------------------------------------------------------------- #
_DDL = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    instruction TEXT,
    status TEXT DEFAULT 'created',
    schema_config TEXT,          -- JSON blob
    total_pages_processed INTEGER DEFAULT 0,
    processing_time_seconds INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    file_type TEXT,
    pages_extracted INTEGER DEFAULT 0,
    page_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'uploaded',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE,
    data TEXT,                   -- JSON array
    schema_used TEXT,            -- JSON object
    status TEXT DEFAULT 'completed',
    total_records INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    description TEXT,
    tags TEXT,                   -- JSON array
    schema_json TEXT,            -- JSON object
    visibility TEXT DEFAULT 'private',
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    task_type TEXT,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    message TEXT,
    result TEXT,                 -- JSON
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
"""

_thread_local = threading.local()

def _get_conn() -> sqlite3.Connection:
    _ensure_dirs()
    if not hasattr(_thread_local, 'conn') or _thread_local.conn is None:
        conn = sqlite3.connect(str(_DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _thread_local.conn = conn
    return _thread_local.conn


_db_initialized = False

def _init_db():
    global _db_initialized
    if _db_initialized:
        return
    _ensure_dirs()
    conn = sqlite3.connect(str(_DB_PATH))
    conn.executescript(_DDL)
    conn.commit()
    conn.close()
    _db_initialized = True

# Initialize on module load
_init_db()


# JSON columns per table that need automatic serialisation/deserialisation
_JSON_COLS: Dict[str, set] = {
    "projects":          {"schema_config"},
    "datasets":          {"data", "schema_used"},
    "schema_templates":  {"tags", "schema_json"},
    "processing_jobs":   {"result"},
}

_NOW = lambda: datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Result wrapper (mirrors supabase-py response)                                #
# --------------------------------------------------------------------------- #
class _Result:
    def __init__(self, data, count: Optional[int] = None, error=None):
        self.data  = data
        if count is not None:
            self.count = count
        elif isinstance(data, list):
            self.count = len(data)
        elif data:
            self.count = 1
        else:
            self.count = 0
        self.error = error


# --------------------------------------------------------------------------- #
# Fluent query builder                                                          #
# --------------------------------------------------------------------------- #
class _Query:
    """Chainable query builder backed by SQLite."""

    def __init__(self, table: str):
        self._table   = table
        self._cols    = "*"
        self._count   = False          # whether .count="exact" was requested
        self._wheres: List[str] = []
        self._params:  List[Any] = []
        self._order_by: Optional[str] = None
        self._order_desc = False
        self._limit:  Optional[int] = None
        self._offset: Optional[int] = None
        self._single  = False
        self._is_insert = False
        self._is_update = False
        self._upsert = False
        self._insert_data: Optional[Dict] = None
        self._update_data: Optional[Dict] = None

    # -------- selection ---------------------------------------------------- #
    def select(self, columns: str = "*", count: Optional[str] = None) -> "_Query":
        self._cols  = columns
        self._count = count == "exact"
        return self

    # -------- filters ------------------------------------------------------- #
    def eq(self, col: str, val: Any) -> "_Query":
        self._wheres.append(f'"{col}" = ?')
        self._params.append(val)
        return self

    def neq(self, col: str, val: Any) -> "_Query":
        self._wheres.append(f'"{col}" != ?')
        self._params.append(val)
        return self

    def is_(self, col: str, val: str) -> "_Query":
        if val == "null":
            self._wheres.append(f'"{col}" IS NULL')
        else:
            self._wheres.append(f'"{col}" IS NOT NULL')
        return self

    def in_(self, col: str, vals: List[Any]) -> "_Query":
        placeholders = ", ".join("?" * len(vals))
        self._wheres.append(f'"{col}" IN ({placeholders})')
        self._params.extend(vals)
        return self

    def not_(self, col: str, op: str, val: Any) -> "_Query":
        self._wheres.append(f'NOT ("{col}" {op} ?)')
        self._params.append(val)
        return self

    # -------- ordering / pagination ---------------------------------------- #
    def order(self, col: str, desc: bool = False) -> "_Query":
        self._order_by   = col
        self._order_desc = desc
        return self

    def range(self, start: int, end: int) -> "_Query":
        self._offset = start
        self._limit  = end - start + 1
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def single(self) -> "_Query":
        self._single = True
        return self

    # -------- mutations ----------------------------------------------------- #
    def insert(self, data: Dict) -> "_Query":
        self._is_insert   = True
        self._insert_data = data
        return self

    def upsert(self, data: Dict) -> "_Query":
        self._is_insert  = True
        self._upsert     = True
        self._insert_data = data
        return self

    def update(self, data: Dict) -> "_Query":
        self._is_update   = True
        self._update_data = data
        return self

    def delete(self) -> "_Query":
        self._is_update   = True
        self._update_data = {"deleted_at": _NOW()}   # soft-delete convention
        return self

    # -------- execution ----------------------------------------------------- #
    def execute(self) -> _Result:
        conn = _get_conn()
        try:
            if self._is_insert:
                return self._exec_insert(conn)
            if self._is_update:
                return self._exec_update(conn)
            return self._exec_select(conn)
        except Exception:
            raise

    # ....................................................................
    def _serialise(self, row: Dict) -> Dict:
        """Convert Python objects to SQLite-storable types."""
        json_cols = _JSON_COLS.get(self._table, set())
        out = {}
        for k, v in row.items():
            if k in json_cols:
                out[k] = json.dumps(v) if v is not None else None
            else:
                out[k] = v
        return out

    def _deserialise(self, row: sqlite3.Row) -> Dict:
        """Convert sqlite3.Row back to Python dict with JSON decoded."""
        d = dict(row)
        json_cols = _JSON_COLS.get(self._table, set())
        for col in json_cols:
            if col in d and d[col] is not None:
                try:
                    d[col] = json.loads(d[col])
                except Exception:
                    pass
        return d

    def _exec_select(self, conn: sqlite3.Connection) -> _Result:
        # Build column list — leave "*" unquoted, quote named columns
        if self._cols == "*":
            clean_cols = "*"
        else:
            clean_cols = ", ".join(
                f'"{c.strip()}"' for c in self._cols.split(",")
                if c.strip() not in ("", ) and "count" not in c.lower()
            ) or "*"

        where_clause = f"WHERE {' AND '.join(self._wheres)}" if self._wheres else ""
        order_clause = ""
        if self._order_by:
            order_clause = f'ORDER BY "{self._order_by}" {"DESC" if self._order_desc else "ASC"}'
        limit_clause  = f"LIMIT {self._limit}"  if self._limit  is not None else ""
        offset_clause = f"OFFSET {self._offset}" if self._offset is not None else ""

        sql = f'SELECT {clean_cols} FROM "{self._table}" {where_clause} {order_clause} {limit_clause} {offset_clause}'
        rows = conn.execute(sql, self._params).fetchall()
        data = [self._deserialise(r) for r in rows]

        count = None
        if self._count:
            count_sql = f'SELECT COUNT(*) FROM "{self._table}" {where_clause}'
            count = conn.execute(count_sql, self._params).fetchone()[0]

        if self._single:
            # Mimic supabase-py: .single() sets .data to the dict itself (or [])
            return _Result(data[0] if data else [], count)
        return _Result(data, count)

    def _exec_insert(self, conn: sqlite3.Connection) -> _Result:
        row = dict(self._insert_data)
        if "id" not in row:
            row["id"] = str(uuid.uuid4())
        if "created_at" not in row:
            row["created_at"] = _NOW()
        if "updated_at" not in row and "created_at" in row:
            row["updated_at"] = row["created_at"]

        row = self._serialise(row)
        cols = ", ".join(f'"{k}"' for k in row)
        placeholders = ", ".join("?" * len(row))
        conflict = "OR REPLACE" if self._upsert else ""
        sql = f'INSERT {conflict} INTO "{self._table}" ({cols}) VALUES ({placeholders})'
        conn.execute(sql, list(row.values()))
        conn.commit()

        # Fetch back
        fetched = conn.execute(f'SELECT * FROM "{self._table}" WHERE "id" = ?', [row["id"]]).fetchone()
        data = [self._deserialise(fetched)] if fetched else []
        return _Result(data)

    def _exec_update(self, conn: sqlite3.Connection) -> _Result:
        row = self._serialise(dict(self._update_data))
        if "updated_at" not in row:
            row["updated_at"] = _NOW()
        set_clause = ", ".join(f'"{k}" = ?' for k in row)
        where_clause = f"WHERE {' AND '.join(self._wheres)}" if self._wheres else ""
        sql = f'UPDATE "{self._table}" SET {set_clause} {where_clause}'
        conn.execute(sql, list(row.values()) + self._params)
        conn.commit()

        # Fetch back updated rows
        select_sql = f'SELECT * FROM "{self._table}" {where_clause}'
        rows = conn.execute(select_sql, self._params).fetchall()
        data = [self._deserialise(r) for r in rows]
        return _Result(data)


# --------------------------------------------------------------------------- #
# Local file storage (mimics supabase.storage)                                 #
# --------------------------------------------------------------------------- #
class _StorageBucket:
    def __init__(self, bucket: str):
        self._dir = _FILES_DIR / bucket

    def upload(self, path: str, content: bytes) -> Any:
        _ensure_dirs()
        dest = self._dir / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        logger.debug(f"Stored file: {dest}")
        return {"path": path}

    def download(self, path: str) -> bytes:
        dest = self._dir / path
        if not dest.exists():
            raise FileNotFoundError(f"File not found in local storage: {path}")
        return dest.read_bytes()

    def get_public_url(self, path: str) -> str:
        # Return a local URL that the backend can serve (informational only)
        return f"local://{self._dir / path}"

    def remove(self, paths: List[str]) -> Any:
        for p in paths:
            f = self._dir / p
            if f.exists():
                f.unlink()
        return {"removed": paths}


class _StorageClient:
    def from_(self, bucket: str) -> _StorageBucket:
        return _StorageBucket(bucket)


# --------------------------------------------------------------------------- #
# Top-level client  (mirrors supabase.create_client return value)              #
# --------------------------------------------------------------------------- #
class LocalClient:
    def __init__(self):
        self.storage = _StorageClient()
        self.auth    = _FakeAuth()

    def table(self, name: str) -> _Query:
        return _Query(name)


class _FakeAuth:
    """Stub – no real auth in local mode."""
    def get_user(self, token: str = "") -> Any:
        return type("R", (), {"user": None})()

    class admin:
        @staticmethod
        def list_users():
            return []


# --------------------------------------------------------------------------- #
# SupabaseService drop-in replacement                                          #
# --------------------------------------------------------------------------- #
class LocalSupabaseService:
    """
    Drop-in replacement for SupabaseService in supabase_client.py.
    Uses SQLite + local filesystem instead of Supabase.
    """

    def __init__(self):
        self.client = LocalClient()

    def get_service_client(self) -> LocalClient:
        return self.client

    async def verify_user_token(self, token: str) -> Optional[Dict[str, Any]]:
        # In local mode every token is valid – return the default local user
        return {"id": "local", "email": "local@qgen.app", "user_metadata": {}, "app_metadata": {}}

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return {
            "id": user_id,
            "subscription_tier": "enterprise",
            "monthly_usage_pages": 0,
            "monthly_usage_mb": 0.0,
        }


# Singleton – used in place of `supabase_service` from supabase_client.py
supabase_service = LocalSupabaseService()

# Also export `supabase` as a LocalClient so that any
# `from .supabase_client import supabase` still works
supabase = supabase_service.client


def get_supabase_client(use_service_role: bool = False) -> LocalClient:
    return supabase_service.client
