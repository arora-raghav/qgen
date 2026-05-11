/**
 * Document processing API client
 * Copied from qelab-ui/client/src/lib/documentApi.ts
 * Auth change: Supabase JWT replaced with optional VITE_API_KEY env var
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';
const API_KEY = (import.meta.env.VITE_API_KEY as string) || '';
const DOCUMENTS_BASE_URL = `${API_BASE_URL}/documents`;

// Types

export interface Project {
  id: string
  name: string
  description?: string
  instruction?: string
  status: string
  created_at: string
  updated_at: string
  user_id: string
}

export interface Document {
  id: string
  project_id: string
  filename: string
  file_size: number
  file_type: string
  page_count: number
  pages_extracted?: number
  status: string
  storage_url: string
  created_at: string
}

export interface UploadedFile {
  id: string
  filename: string
  size_mb: number
  page_count: number
  file_type: string
  status: string
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message: string
}

export interface UploadResponse {
  uploaded_files: UploadedFile[]
  errors: string[]
  total_uploaded: number
  total_errors: number
  total_pages: number
}

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message: string
  task_type?: string
  result?: any
  error?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface Schema {
  schema: any
  mode?: 'business' | 'qa'
  instruction?: string
  status?: string
  generated_from?: number
  created_at?: string
  updated_at?: string
}

export interface SchemaFieldInput {
  key: string
  type: 'string' | 'number' | 'integer' | 'boolean' | 'date' | 'datetime' | 'enum'
  required?: boolean
  description?: string
}

export interface SchemaPutRequestBody {
  schema: {
    name?: string;
    fields: SchemaFieldInput[];
  };
  instruction?: string;
}

export interface SchemaTemplate {
  id: string;
  name: string;
  category?: string;
  description?: string;
  tags?: string[];
  visibility: 'private' | 'builtin';
  schema_json: any;
  created_at: string;
}

export interface ProcessingJob {
  id: string;
  project_id: string;
  job_type: string;
  status: string;
  progress: number;
  message: string;
  result?: any;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface PreviewRequest {
  num_records?: number;
  chunk_strategy?: 'top' | 'random';
  max_chunk_chars?: number;
  temperature?: number;
}

export interface PreviewResponse {
  records: any[];
  validation: {
    summary: { total: number; valid: number; invalid: number };
    issues: Array<{ row: number; field: string; type: string; message: string }>;
  };
  used_chunks: { count: number; chars: number };
  elapsed_ms: number;
}

export interface Dataset {
  records: any[]
  total_records: number
  schema?: any
  status?: string
  offset: number
  limit: number
}

// ─── Auth Headers ─────────────────────────────────────────────────────────────

function getHeaders(): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (API_KEY) headers['Authorization'] = `Bearer ${API_KEY}`
  return headers
}

function getFormDataHeaders(): HeadersInit {
  const headers: Record<string, string> = {}
  if (API_KEY) headers['Authorization'] = `Bearer ${API_KEY}`
  return headers
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const documentApi = {
  // Projects
  async getProjects(): Promise<Project[]> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects`, { method: 'GET', headers: getHeaders() })
    if (!res.ok) throw new Error(`Failed to fetch projects: ${res.statusText}`)
    const result: ApiResponse<{projects: Project[], pagination: any}> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to fetch projects')
    return result.data?.projects || []
  },

  async createProject(data: { name: string; description?: string; instruction?: string }): Promise<Project> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects`, {
      method: 'POST', headers: getHeaders(), body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(`Failed to create project: ${res.statusText}`)
    const result: ApiResponse<Project> = await res.json()
    if (!result.success) throw new Error(result.message)
    return result.data!
  },

  async getProject(projectId: string): Promise<Project> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}`, { method: 'GET', headers: getHeaders() })
    if (!res.ok) throw new Error(`Failed to fetch project: ${res.statusText}`)
    const result: ApiResponse<Project> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to fetch project')
    return result.data!
  },

  async updateProject(projectId: string, updates: { name?: string; description?: string; instruction?: string }): Promise<Project> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}`, {
      method: 'PATCH', headers: getHeaders(), body: JSON.stringify(updates),
    })
    if (!res.ok) throw new Error(`Failed to update project: ${res.statusText}`)
    const result: ApiResponse<Project> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to update project')
    return result.data!
  },

  async deleteProject(projectId: string): Promise<void> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}`, {
      method: 'DELETE', headers: getHeaders(),
    })
    if (!res.ok) throw new Error(`Failed to delete project: ${res.statusText}`)
  },

  // Documents
  async uploadDocuments(projectId: string, files: File[]): Promise<UploadResponse> {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/documents/upload`, {
      method: 'POST', headers: getFormDataHeaders(), body: formData,
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
    const result: ApiResponse<UploadResponse> = await res.json()
    if (!result.success) throw new Error(result.message)
    return result.data!
  },

  async getProjectDocuments(projectId: string): Promise<Document[]> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/documents`, { headers: getHeaders() })
    if (!res.ok) throw new Error(`Failed to get documents: ${res.statusText}`)
    const result: ApiResponse<{ documents: Document[] }> = await res.json()
    if (!result.success) throw new Error(result.message)
    return result.data!.documents
  },

  async deleteDocument(projectId: string, documentId: string): Promise<void> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/documents/${documentId}`, {
      method: 'DELETE', headers: getHeaders(),
    })
    if (!res.ok) throw new Error(`Failed to delete document: ${res.statusText}`)
  },

  async getUserProfile(): Promise<any> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/user/profile`, { method: 'GET', headers: getHeaders() })
    if (!res.ok) throw new Error(`Failed to fetch user profile: ${res.statusText}`)
    const result: ApiResponse = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to fetch user profile')
    return result.data
  },

  // Schema
  async generateSchema(projectId: string, customInstruction?: string, mode: 'business' | 'qa' = 'business', selectedDocumentIds?: string[]): Promise<{ task_id: string }> {
    const instruction = customInstruction || 'Generate a schema based on the uploaded documents'
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/schema/generate`, {
      method: 'POST', headers: getHeaders(),
      body: JSON.stringify({ mode, instruction, selected_document_ids: selectedDocumentIds }),
    })
    if (!res.ok) throw new Error(`Failed to generate schema: ${res.statusText}`)
    const result: ApiResponse<{ task_id: string }> = await res.json()
    if (!result.success) throw new Error(result.message)
    return result.data!
  },

  async getProjectSchema(projectId: string): Promise<Schema | null> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/schema`, { headers: getHeaders() })
    if (!res.ok) return null
    const result: ApiResponse<Schema> = await res.json()
    return result.success ? result.data! : null
  },

  // Dataset
  async generateDataset(projectId: string, numRecords: number = 50): Promise<{ task_id: string }> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/generate`, {
      method: 'POST', headers: getHeaders(),
      body: JSON.stringify({ num_records: numRecords }),
    })
    if (!res.ok) throw new Error(`Failed to generate dataset: ${res.statusText}`)
    const result: ApiResponse<{ task_id: string }> = await res.json()
    if (!result.success) throw new Error(result.message)
    return result.data!
  },

  async getProjectDataset(projectId: string, limit = 500, offset = 0): Promise<Dataset | null> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/dataset?limit=${limit}&offset=${offset}`, {
      headers: getHeaders(),
    })
    if (!res.ok) return null
    const result: ApiResponse<Dataset> = await res.json()
    return result.success ? result.data! : null
  },

  async getProjectJobs(projectId: string): Promise<ProcessingJob[]> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/jobs`, { method: 'GET', headers: getHeaders() })
    if (!res.ok) throw new Error(`Failed to get jobs: ${res.statusText}`)
    const result: ApiResponse<{ jobs: ProcessingJob[] }> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to get jobs')
    return result.data!.jobs
  },

  // Task polling
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/tasks/${taskId}/status`, { headers: getHeaders() })
    if (!res.ok) throw new Error(`Failed to get task status: ${res.statusText}`)
    const result: ApiResponse<TaskStatus> = await res.json()
    if (!result.success) throw new Error(result.message)
    return result.data!
  },

  async updateProjectSchema(projectId: string, payload: SchemaPutRequestBody): Promise<{ schema: any }> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/schema`, {
      method: 'PUT', headers: getHeaders(), body: JSON.stringify(payload),
    })
    if (!res.ok) { const text = await res.text(); throw new Error(`Failed to update schema: ${res.statusText} ${text}`) }
    const result: ApiResponse<{ schema: any }> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to update schema')
    return result.data!
  },

  async listSchemaTemplates(category?: string, q?: string): Promise<{ builtin: SchemaTemplate[]; mine: SchemaTemplate[] }> {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    if (q) params.set('q', q)
    const res = await fetch(`${DOCUMENTS_BASE_URL}/schema-templates?${params.toString()}`, { method: 'GET', headers: getHeaders() })
    if (!res.ok) throw new Error(`Failed to list templates: ${res.statusText}`)
    const result: ApiResponse<{ builtin: SchemaTemplate[]; mine: SchemaTemplate[] }> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to list templates')
    return result.data!
  },

  async createSchemaTemplate(payload: { name: string; category?: string; description?: string; tags?: string[]; schema_json: any }): Promise<SchemaTemplate> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/schema-templates`, {
      method: 'POST', headers: getHeaders(), body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`Failed to create template: ${res.statusText}`)
    const result: ApiResponse<SchemaTemplate> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to create template')
    return result.data!
  },

  async applySchemaTemplate(projectId: string, templateId: string): Promise<{ schema: any }> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/schema/apply-template/${templateId}`, {
      method: 'POST', headers: getHeaders(),
    })
    if (!res.ok) throw new Error(`Failed to apply template: ${res.statusText}`)
    const result: ApiResponse<{ schema: any }> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to apply template')
    return result.data!
  },

  async generateSchemaPreview(projectId: string, req: PreviewRequest): Promise<PreviewResponse> {
    const res = await fetch(`${DOCUMENTS_BASE_URL}/projects/${projectId}/schema/preview`, {
      method: 'POST', headers: getHeaders(), body: JSON.stringify(req),
    })
    if (!res.ok) { const text = await res.text(); throw new Error(`Failed to generate preview: ${res.statusText} ${text}`) }
    const result: ApiResponse<PreviewResponse> = await res.json()
    if (!result.success) throw new Error(result.message || 'Failed to generate preview')
    return result.data!
  },
}

export default documentApi
