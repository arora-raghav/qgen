import React, { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import FileUpload, { type FileWithPreview } from '@/components/FileUpload'
import { documentApi, type Schema, type TaskStatus } from '@/lib/api'
import {
  Upload, Sparkles, Database, Download, CheckCircle, Loader2,
  ChevronRight, RotateCcw, FileJson, FileText, AlertCircle,
} from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────

type Step = 'upload' | 'schema' | 'generate' | 'export'

const STEPS: { id: Step; label: string; icon: React.ReactNode }[] = [
  { id: 'upload',   label: 'Upload',   icon: <Upload className="h-4 w-4" /> },
  { id: 'schema',   label: 'Schema',   icon: <Sparkles className="h-4 w-4" /> },
  { id: 'generate', label: 'Generate', icon: <Database className="h-4 w-4" /> },
  { id: 'export',   label: 'Export',   icon: <Download className="h-4 w-4" /> },
]

const STEP_ORDER: Step[] = ['upload', 'schema', 'generate', 'export']

// ─── Helpers ──────────────────────────────────────────────────────────────────

const getOrderedKeys = (data: any[]): string[] => {
  if (!data.length) return []
  const preferred = ['topic', 'question', 'answer', 'keywords', 'difficulty', 'context', 'explanation']
  const all = Object.keys(data[0])
  const map = new Map(all.map(k => [k.toLowerCase(), k]))
  return preferred.filter(p => map.has(p)).map(p => map.get(p)!)
    .concat(all.filter(k => !preferred.includes(k.toLowerCase())))
}

const toCSV = (data: any[]): string => {
  if (!data.length) return ''
  const keys = getOrderedKeys(data)
  const rows = data.map(row =>
    keys.map(k => `"${String(row[k] ?? '').replace(/"/g, '""')}""`).join(',')
  )
  return [keys.join(','), ...rows].join('\n')
}

const downloadFile = (content: string, name: string, mime: string) => {
  const url = URL.createObjectURL(new Blob([content], { type: mime }))
  Object.assign(document.createElement('a'), { href: url, download: name }).click()
  URL.revokeObjectURL(url)
}

function pollTask(
  taskId: string,
  onProgress: (t: TaskStatus) => void,
  signal: AbortSignal
): Promise<TaskStatus> {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      if (signal.aborted) { reject(new Error('Aborted')); return }
      try {
        const status = await documentApi.getTaskStatus(taskId)
        onProgress(status)
        if (status.status === 'completed') { resolve(status); return }
        if (status.status === 'failed' || status.status === 'cancelled') {
          reject(new Error(status.error || 'Task failed')); return
        }
        setTimeout(tick, 2000)
      } catch (e) { reject(e) }
    }
    tick()
  })
}

// ─── Step Header ──────────────────────────────────────────────────────────────

const StepBar: React.FC<{ current: Step; completed: Set<Step> }> = ({ current, completed }) => (
  <div className="flex items-center gap-1 mb-8">
    {STEPS.map((s, i) => {
      const isActive = s.id === current
      const isDone = completed.has(s.id)
      return (
        <React.Fragment key={s.id}>
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            isDone ? 'bg-green-100 text-green-700' : isActive ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'
          }`}>
            {isDone ? <CheckCircle className="h-4 w-4" /> : s.icon}
            <span className="hidden sm:inline">{s.label}</span>
          </div>
          {i < STEPS.length - 1 && (
            <ChevronRight className={`h-4 w-4 flex-shrink-0 ${isDone ? 'text-green-400' : 'text-gray-300'}`} />
          )}
        </React.Fragment>
      )
    })}
  </div>
)

// ─── Main Page ────────────────────────────────────────────────────────────────

const WorkflowPage: React.FC = () => {
  const { toast } = useToast()

  // State
  const [step, setStep] = useState<Step>('upload')
  const [completed, setCompleted] = useState<Set<Step>>(new Set())

  // Step 1 — Upload
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const [projectId, setProjectId] = useState<string | null>(null)
  const [projectName, setProjectName] = useState('')
  const [uploadDone, setUploadDone] = useState(false)

  // Step 2 — Schema
  const [schemaInstruction, setSchemaInstruction] = useState('')
  const [schemaMode, setSchemaMode] = useState<'qa' | 'business'>('qa')
  const [schemaTask, setSchemaTask] = useState<TaskStatus | null>(null)
  const [schema, setSchema] = useState<Schema | null>(null)
  const [generatingSchema, setGeneratingSchema] = useState(false)

  // Step 3 — Generate
  const [numRecords, setNumRecords] = useState(50)
  const [datasetTask, setDatasetTask] = useState<TaskStatus | null>(null)
  const [dataset, setDataset] = useState<any[]>([])
  const [generatingDataset, setGeneratingDataset] = useState(false)

  const abortRef = useRef<AbortController | null>(null)

  const markDone = (s: Step) => setCompleted(prev => new Set([...prev, s]))
  const advance = (to: Step) => { setStep(to) }
  const reset = () => {
    setStep('upload'); setCompleted(new Set())
    setFiles([]); setProjectId(null); setProjectName(''); setUploadDone(false)
    setSchemaInstruction(''); setSchemaTask(null); setSchema(null)
    setDatasetTask(null); setDataset([]); setNumRecords(50)
    abortRef.current?.abort()
  }

  // ── Step 1: handle upload complete ──────────────────────────────────────────
  const handleCreateAndUpload = async () => {
    const pendingFiles = files.filter(f => f.status === 'pending')
    if (!pendingFiles.length) {
      toast({ title: 'No files', description: 'Add at least one file to upload', variant: 'destructive' })
      return
    }
    // Project is created first; the FileUpload component handles the upload.
    // We create the project here so its ID is available when FileUpload calls uploadDocuments.
    if (!projectId) {
      try {
        const name = projectName.trim() || `Project ${new Date().toLocaleDateString()}`
        const proj = await documentApi.createProject({ name, description: 'Created by QGen' })
        setProjectId(proj.id)
        setProjectName(proj.name)
        toast({ title: 'Project created', description: proj.name })
      } catch (e: any) {
        toast({ title: 'Error', description: e.message, variant: 'destructive' })
      }
    }
  }

  const handleUploadComplete = () => {
    setUploadDone(true)
    markDone('upload')
  }

  // ── Step 2: generate schema ──────────────────────────────────────────────────
  const handleGenerateSchema = async () => {
    if (!projectId) return
    setGeneratingSchema(true)
    setSchemaTask(null)
    abortRef.current = new AbortController()
    try {
      const { task_id } = await documentApi.generateSchema(projectId, schemaInstruction || undefined, schemaMode)
      const final = await pollTask(task_id, setSchemaTask, abortRef.current.signal)
      const s = await documentApi.getProjectSchema(projectId)
      setSchema(s)
      markDone('schema')
      toast({ title: 'Schema ready', description: `${Object.keys(s?.schema?.properties || s?.schema?.fields || {}).length} fields generated` })
    } catch (e: any) {
      if (e.message !== 'Aborted') toast({ title: 'Schema generation failed', description: e.message, variant: 'destructive' })
    } finally {
      setGeneratingSchema(false)
    }
  }

  // ── Step 3: generate dataset ─────────────────────────────────────────────────
  const handleGenerateDataset = async () => {
    if (!projectId) return
    setGeneratingDataset(true)
    setDatasetTask(null)
    abortRef.current = new AbortController()
    try {
      const { task_id } = await documentApi.generateDataset(projectId, numRecords)
      await pollTask(task_id, setDatasetTask, abortRef.current.signal)
      const ds = await documentApi.getProjectDataset(projectId, numRecords)
      setDataset(ds?.records || [])
      markDone('generate')
      toast({ title: 'Dataset ready', description: `${ds?.total_records ?? ds?.records?.length} records generated` })
    } catch (e: any) {
      if (e.message !== 'Aborted') toast({ title: 'Dataset generation failed', description: e.message, variant: 'destructive' })
    } finally {
      setGeneratingDataset(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  const schemaFields: string[] = (() => {
    if (!schema?.schema) return []
    const s = schema.schema
    if (s.properties) return Object.keys(s.properties)
    if (s.fields) return s.fields.map((f: any) => f.key || f.name)
    return []
  })()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-lg text-gray-900">QGen</span>
            <Badge variant="outline" className="text-xs">Document Extractor</Badge>
          </div>
          {step !== 'upload' && (
            <Button variant="ghost" size="sm" onClick={reset}>
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
              Start over
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <StepBar current={step} completed={completed} />

        {/* ─── STEP 1: Upload ─────────────────────────────────────────────────── */}
        {step === 'upload' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Upload Documents</h1>
              <p className="text-gray-500 mt-1">Add the source documents you want to extract training data from.</p>
            </div>

            <div className="space-y-2">
              <Label>Project name <span className="text-gray-400 font-normal">(optional)</span></Label>
              <Input
                placeholder={`e.g. Legal contracts Q3 · defaults to today's date`}
                value={projectName}
                onChange={e => setProjectName(e.target.value)}
                disabled={!!projectId}
              />
            </div>

            {!projectId ? (
              <>
                <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                  Click <strong>Create project</strong> first, then upload your files.
                </div>
                <Button onClick={handleCreateAndUpload} className="w-full bg-blue-600 hover:bg-blue-700">
                  Create project & start uploading
                </Button>
              </>
            ) : (
              <>
                <FileUpload
                  projectId={projectId}
                  files={files}
                  setFiles={setFiles}
                  onUploadComplete={handleUploadComplete}
                />
                {uploadDone && (
                  <Button onClick={() => advance('schema')} className="w-full bg-blue-600 hover:bg-blue-700">
                    Continue to Schema Generation
                    <ChevronRight className="h-4 w-4 ml-2" />
                  </Button>
                )}
              </>
            )}
          </div>
        )}

        {/* ─── STEP 2: Schema ──────────────────────────────────────────────────── */}
        {step === 'schema' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Generate Schema</h1>
              <p className="text-gray-500 mt-1">Tell the AI what kind of data to extract, then generate a field schema.</p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Extraction mode</Label>
                <Select value={schemaMode} onValueChange={(v: 'qa' | 'business') => setSchemaMode(v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="qa">Q&amp;A pairs — question / answer / context</SelectItem>
                    <SelectItem value="business">Business data — entities, facts, structured fields</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Instruction <span className="text-gray-400 font-normal">(optional)</span></Label>
                <Textarea
                  placeholder="e.g. Extract Q&A pairs about financial figures and risk factors"
                  value={schemaInstruction}
                  onChange={e => setSchemaInstruction(e.target.value)}
                  rows={3}
                  disabled={generatingSchema}
                />
              </div>
            </div>

            {/* Progress */}
            {generatingSchema && schemaTask && (
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center gap-2 text-blue-800">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm font-medium">{schemaTask.message || 'Generating schema…'}</span>
                  </div>
                  <Progress value={schemaTask.progress} className="h-2" />
                  <p className="text-xs text-blue-600">{Math.round(schemaTask.progress)}% complete</p>
                </CardContent>
              </Card>
            )}

            {/* Schema result */}
            {schema && schemaFields.length > 0 && (
              <Card className="border-green-200 bg-green-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-green-800 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Schema ready — {schemaFields.length} fields
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex flex-wrap gap-1.5">
                    {schemaFields.map(f => (
                      <Badge key={f} variant="outline" className="text-xs font-mono border-green-300 text-green-800 bg-white">
                        {f}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex gap-3">
              <Button variant="outline" onClick={() => advance('upload')}>Back</Button>
              <Button
                onClick={handleGenerateSchema}
                disabled={generatingSchema}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
              >
                {generatingSchema
                  ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating…</>
                  : schema ? 'Regenerate Schema' : <>Generate Schema <Sparkles className="h-4 w-4 ml-2" /></>}
              </Button>
              {schema && (
                <Button onClick={() => advance('generate')} className="bg-green-600 hover:bg-green-700">
                  Next <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              )}
            </div>
          </div>
        )}

        {/* ─── STEP 3: Generate Dataset ─────────────────────────────────────────── */}
        {step === 'generate' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Generate Dataset</h1>
              <p className="text-gray-500 mt-1">Choose how many records to generate from your documents.</p>
            </div>

            <div className="space-y-2">
              <Label>Number of records</Label>
              <div className="flex items-center gap-3">
                <Input
                  type="number"
                  min={1}
                  max={10000}
                  value={numRecords}
                  onChange={e => setNumRecords(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-36"
                  disabled={generatingDataset}
                />
                <div className="flex gap-2">
                  {[25, 50, 100, 250].map(n => (
                    <Button key={n} size="sm" variant={numRecords === n ? 'default' : 'outline'} onClick={() => setNumRecords(n)} disabled={generatingDataset}>
                      {n}
                    </Button>
                  ))}
                </div>
              </div>
            </div>

            {/* Progress */}
            {generatingDataset && datasetTask && (
              <Card className="border-purple-200 bg-purple-50">
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center gap-2 text-purple-800">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm font-medium">{datasetTask.message || 'Generating dataset…'}</span>
                  </div>
                  <Progress value={datasetTask.progress} className="h-2" />
                  <p className="text-xs text-purple-600">{Math.round(datasetTask.progress)}% · This may take a few minutes for large batches</p>
                </CardContent>
              </Card>
            )}

            {/* Sample preview */}
            {dataset.length > 0 && (
              <Card className="border-green-200 bg-green-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-green-800 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    {dataset.length} records ready — sample preview
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <pre className="text-xs bg-white rounded border p-3 max-h-40 overflow-auto text-gray-700">
                    {JSON.stringify(dataset[0], null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}

            <div className="flex gap-3">
              <Button variant="outline" onClick={() => advance('schema')}>Back</Button>
              <Button
                onClick={handleGenerateDataset}
                disabled={generatingDataset}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
              >
                {generatingDataset
                  ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Generating…</>
                  : dataset.length ? 'Regenerate' : <>Generate {numRecords} Records <Database className="h-4 w-4 ml-2" /></>}
              </Button>
              {dataset.length > 0 && (
                <Button onClick={() => advance('export')} className="bg-green-600 hover:bg-green-700">
                  Export <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              )}
            </div>
          </div>
        )}

        {/* ─── STEP 4: Export ──────────────────────────────────────────────────── */}
        {step === 'export' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Export Dataset</h1>
              <p className="text-gray-500 mt-1">{dataset.length} records ready to download.</p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <Card className="hover:shadow-md transition-shadow cursor-pointer border-2 hover:border-blue-300"
                onClick={() => downloadFile(JSON.stringify(dataset, null, 2), `${projectName || 'dataset'}.json`, 'application/json')}>
                <CardContent className="p-6 flex flex-col items-center text-center gap-3">
                  <div className="p-3 bg-blue-100 rounded-xl">
                    <FileJson className="h-8 w-8 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-semibold">JSON</p>
                    <p className="text-xs text-gray-500">{dataset.length} records · pretty-printed</p>
                  </div>
                  <Button className="w-full bg-blue-600 hover:bg-blue-700">
                    <Download className="h-4 w-4 mr-2" />Download JSON
                  </Button>
                </CardContent>
              </Card>

              <Card className="hover:shadow-md transition-shadow cursor-pointer border-2 hover:border-green-300"
                onClick={() => downloadFile(toCSV(dataset), `${projectName || 'dataset'}.csv`, 'text/csv')}>
                <CardContent className="p-6 flex flex-col items-center text-center gap-3">
                  <div className="p-3 bg-green-100 rounded-xl">
                    <FileText className="h-8 w-8 text-green-600" />
                  </div>
                  <div>
                    <p className="font-semibold">CSV</p>
                    <p className="text-xs text-gray-500">{dataset.length} rows · spreadsheet-ready</p>
                  </div>
                  <Button className="w-full bg-green-600 hover:bg-green-700">
                    <Download className="h-4 w-4 mr-2" />Download CSV
                  </Button>
                </CardContent>
              </Card>
            </div>

            {/* Preview table */}
            {dataset.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Preview (first 5 rows)</CardTitle>
                </CardHeader>
                <CardContent className="p-0 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        {getOrderedKeys(dataset).map(k => (
                          <th key={k} className="px-3 py-2 text-left font-medium text-gray-600 whitespace-nowrap">{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dataset.slice(0, 5).map((row, i) => (
                        <tr key={i} className="border-b last:border-0 hover:bg-gray-50">
                          {getOrderedKeys(dataset).map(k => (
                            <td key={k} className="px-3 py-2 text-gray-700 max-w-xs truncate">{String(row[k] ?? '')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}

            <div className="flex gap-3">
              <Button variant="outline" onClick={() => advance('generate')}>Back</Button>
              <Button onClick={reset} className="flex-1">
                <RotateCcw className="h-4 w-4 mr-2" />Process another batch
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default WorkflowPage
