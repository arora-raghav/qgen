import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowLeft, 
  Upload, 
  FileText, 
  Settings, 
  Download,
  Database,
  Clock,
  Trash2,
  CheckCircle,
  AlertCircle,
  Loader2,
  Sparkles,
  Info
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { documentApi, type Project, type UploadResponse, type Document, type Schema, type Dataset, type TaskStatus, type ProcessingJob, type SchemaFieldInput, type SchemaTemplate, type PreviewResponse } from '@/lib/api';
import { calculateQAQualityMetrics, type QAQualityMetrics, type QARecord } from '@/lib/qaQualityAnalysis';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import FileUpload, { type FileWithPreview } from '@/components/FileUpload';
import { Label } from '@/components/ui/label';
import { DialogDescription, DialogFooter } from '@/components/ui/dialog';

// Helper functions for data export
const getOrderedKeys = (data: any[]): string[] => {
  if (data.length === 0) return [];
  
  // Define the preferred column order (case-insensitive)
  const preferredOrder = ['topic', 'question', 'answer', 'keywords', 'difficulty', 'context', 'explanation'];
  const allKeys = Object.keys(data[0]);
  
  // Create a case-insensitive lookup for existing keys
  const keyMap = new Map();
  allKeys.forEach(key => {
    keyMap.set(key.toLowerCase(), key);
  });
  
  // Use preferred order for columns that exist, then append any remaining columns
  return preferredOrder
    .filter(prefKey => keyMap.has(prefKey))
    .map(prefKey => keyMap.get(prefKey))
    .concat(allKeys.filter(key => !preferredOrder.includes(key.toLowerCase())));
};

const convertToCSV = (data: any[]): string => {
  if (data.length === 0) return '';
  
  const orderedKeys = getOrderedKeys(data);
  const csvHeaders = orderedKeys.join(',');
  
  const csvRows = data.map(row => 
    orderedKeys.map(header => {
      const value = row[header];
      const stringValue = typeof value === 'object' ? JSON.stringify(value).replace(/"/g, '""') : String(value).replace(/"/g, '""');
      return `"${stringValue}"`;
    }).join(',')
  );
  
  return [csvHeaders, ...csvRows].join('\n');
};

const downloadFile = (content: string, filename: string, mimeType: string) => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

const ProjectDetail: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [user, setUser] = useState<any>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [schema, setSchema] = useState<Schema | null>(null);
  const [datasetDialogOpen, setDatasetDialogOpen] = useState(false);
  const [customNumRecords, setCustomNumRecords] = useState(50);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [processingJobs, setProcessingJobs] = useState<ProcessingJob[]>([]);
  const [activeTask, setActiveTask] = useState<TaskStatus | null>(null);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [loadingDataset, setLoadingDataset] = useState(false);
  // Schema Builder state
  const [editingFields, setEditingFields] = useState<SchemaFieldInput[]>([]);
  const [schemaDirty, setSchemaDirty] = useState(false);
  const [schemaErrors, setSchemaErrors] = useState<string | null>(null);
  const [templateDrawerOpen, setTemplateDrawerOpen] = useState(false);
  const [templates, setTemplates] = useState<{ builtin: SchemaTemplate[]; mine: SchemaTemplate[] } | null>(null);
  const [templateQuery, setTemplateQuery] = useState('');
  const [instructionOpen, setInstructionOpen] = useState(false);
  const [instructionText, setInstructionText] = useState('');
  const [schemaMode, setSchemaMode] = useState<'business' | 'qa'>('business');
  const [saveTemplateOpen, setSaveTemplateOpen] = useState(false);
  const [templateName, setTemplateName] = useState('');
  const [templateCategory, setTemplateCategory] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [previewCount, setPreviewCount] = useState(5);
  const [previewStrategy, setPreviewStrategy] = useState<'top' | 'random'>('top');
  const [previewTemp, setPreviewTemp] = useState(0.4);
  // Add file state to persist across tab switches
  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([]);
  // Quality analysis state
  const [qualityMetrics, setQualityMetrics] = useState<QAQualityMetrics | null>(null);
  const [qualityAnalysisLoading, setQualityAnalysisLoading] = useState(false);
  // Delete document dialog state
  const [showDeleteDocDialog, setShowDeleteDocDialog] = useState(false);
  const [docToDelete, setDocToDelete] = useState<{id: string, filename: string} | null>(null);

  // Calculate basic quality metrics (for Step 4)
  const calculateBasicQualityMetrics = useCallback(() => {
    if (!dataset || !schema || schema.mode !== 'qa') {
      return;
    }

    try {
      // Convert dataset records to QARecord format
      const qaRecords: QARecord[] = dataset.records.map(record => ({
        question: record.question || '',
        answer: record.answer || '',
        context: record.context || '',
        difficulty: record.difficulty || '',
        topic: record.topic || '',
        question_type: record.question_type || '',
        explanation: record.explanation || '',
        keywords: record.keywords || '',
        ...record // Include any additional fields
      }));

      // Calculate quality metrics
      const metrics = calculateQAQualityMetrics(qaRecords);
      setQualityMetrics(metrics);
    } catch (error) {
      console.error('Error calculating basic quality metrics:', error);
    }
  }, [dataset, schema]);
  
  // Step-by-step workflow state
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [isGeneratingSchema, setIsGeneratingSchema] = useState(false);
  const [isGeneratingDataset, setIsGeneratingDataset] = useState(false);
  const [manualNavigation, setManualNavigation] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set([1])); // Step 1 is always accessible
  
  const { toast } = useToast();

  // No auth — set a default local user immediately
  useEffect(() => {
    setUser({ id: 'local', email: 'local@qgen.app' });
  }, []);

  // Load project details (optimized - only load essential data initially)
  useEffect(() => {
    if (projectId && !project) {
      // Only load if we don't have the data yet (prevents unnecessary re-fetching)
      loadProject();
      loadDocuments();
      // Also load schema and dataset to restore progress state
      loadSchema();
      loadDataset();
    }
  }, [user, projectId]);

  // Poll for active task updates
  useEffect(() => {
    if (activeTask) {
      // Handle immediate completion detection
      if (activeTask.status === 'completed' || activeTask.status === 'failed') {
        const handleCompletion = async () => {
          if (activeTask.task_type === 'schema_generation') {
            await loadSchema();
            if (activeTask.status === 'completed') {
              setCompletedSteps(prev => new Set([...Array.from(prev), 3]));
              setCurrentStep(3);
              toast({
                title: "Schema Generated Successfully",
                description: "Your schema has been generated. You can now preview and generate datasets.",
              });
            } else {
              toast({
                title: "Schema Generation Failed",
                description: "Please try again or check your documents.",
                variant: "destructive"
              });
            }
          } else if (activeTask.task_type === 'dataset_generation') {
            await loadDataset();
            if (activeTask.status === 'completed') {
              setCompletedSteps(prev => new Set([...Array.from(prev), 4]));
              setCurrentStep(4);
              toast({
                title: "Dataset Generated Successfully",
                description: "Your dataset has been generated. You can now export your data.",
              });
            } else {
              toast({
                title: "Dataset Generation Failed",
                description: "Please try again or check your schema.",
                variant: "destructive"
              });
            }
          }
          setActiveTask(null);
        };
        
        handleCompletion();
        return; // Exit early if already completed
      }
      
      // Continue polling for running/pending tasks
      if (activeTask.status === 'running' || activeTask.status === 'pending') {
        const interval = setInterval(async () => {
          try {
            const taskStatus = await documentApi.getTaskStatus(activeTask.task_id);
            setActiveTask(taskStatus);
            
            if (taskStatus.status === 'completed' || taskStatus.status === 'failed') {
              // Only reload specific data based on task type (more efficient)
              if (taskStatus.task_type === 'schema_generation') {
                await loadSchema(); // Make sure schema loads before proceeding
                if (taskStatus.status === 'completed') {
                  // Mark step 3 as accessible and advance to it when schema generation completes
                  setCompletedSteps(prev => new Set([...Array.from(prev), 3]));
                  setCurrentStep(3);
                  toast({
                    title: "Schema Generated Successfully",
                    description: "Your schema has been generated. You can now preview and generate datasets.",
                  });
                } else {
                  // Stay on Documents tab with error message
                  toast({
                    title: "Schema Generation Failed",
                    description: "Please try again or check your documents.",
                    variant: "destructive"
                  });
                }
              } else if (taskStatus.task_type === 'dataset_generation') {
                await loadDataset(); // Make sure dataset loads before proceeding
                if (taskStatus.status === 'completed') {
                  // Mark step 4 as accessible and advance to it when dataset generation completes
                  setCompletedSteps(prev => new Set([...Array.from(prev), 4]));
                  setCurrentStep(4);
                  toast({
                    title: "Dataset Generated Successfully",
                    description: "Your dataset has been generated. You can now export your data.",
                  });
                } else {
                  // Stay on Schema tab with error message
                  toast({
                    title: "Dataset Generation Failed",
                    description: "Please try again or check your schema.",
                    variant: "destructive"
                  });
                }
              }
              setActiveTask(null);
            }
          } catch (error) {
            console.error('Error polling task status:', error);
          }
        }, 2000); // Poll every 2 seconds

        return () => clearInterval(interval);
      }
    }
  }, [activeTask]);

  useEffect(() => {
    if (user) {
      loadUserProfile();
    }
  }, [user]);

  // Step progression logic - only auto-advance on specific actions, not when documents exist
  useEffect(() => {
    // Don't auto-advance if user just manually navigated
    if (manualNavigation) {
      // Use setTimeout to reset the flag after all effects have run
      const timer = setTimeout(() => setManualNavigation(false), 100);
      return () => clearTimeout(timer);
    }
    
    // If both schema and dataset already exist, don't auto-advance - let user navigate freely
    if (schema && dataset) {
      return;
    }
    
    // Step 3: Generate Schema - move to step 3 when schema is generated (only if on step 2)
    if (schema && currentStep === 2) {
      setCompletedSteps(prev => new Set([...Array.from(prev), 3]));
      setCurrentStep(3);
      return;
    }
    
    // Step 4: Export Dataset - move to step 4 when dataset is generated (only if on step 3)
    if (dataset && currentStep === 3) {
      setCompletedSteps(prev => new Set([...Array.from(prev), 4]));
      setCurrentStep(4);
      return;
    }
    
  // Step 5: Data Quality - accessible when dataset exists (only for Q&A mode)
  if (dataset && schema?.mode === 'qa' && !completedSteps.has(5)) {
    setCompletedSteps(prev => new Set([...Array.from(prev), 5]));
    
    // Auto-calculate quality metrics when dataset is generated
    if (!qualityMetrics) {
      calculateBasicQualityMetrics();
    }
  }
  }, [schema, dataset, currentStep, manualNavigation]);

  // Initialize completed steps based on existing data (on initial load only)
  useEffect(() => {
    // Only run this once when data is first loaded, not on every change
    if (project && !completedSteps.has(2) && documents.length > 0) {
      // Documents exist, so step 2 should be accessible
      setCompletedSteps(prev => new Set([...Array.from(prev), 2]));
    }
    if (schema && !completedSteps.has(3)) {
      // Schema exists, so step 3 should be accessible
      setCompletedSteps(prev => new Set([...Array.from(prev), 3]));
    }
    if (dataset && !completedSteps.has(4)) {
      // Dataset exists, so step 4 should be accessible
      setCompletedSteps(prev => new Set([...Array.from(prev), 4]));
    }
    if (dataset && schema?.mode === 'qa' && !completedSteps.has(5)) {
      // Q&A dataset exists, so step 5 should be accessible
      setCompletedSteps(prev => new Set([...Array.from(prev), 5]));
      
      // Auto-calculate quality metrics if not already calculated
      if (!qualityMetrics) {
        calculateBasicQualityMetrics();
      }
    }
  }, [project, documents.length, schema, dataset, qualityMetrics, calculateBasicQualityMetrics]); // Don't include manualNavigation or completedSteps

  // Auto-calculate quality metrics when dataset is generated
  useEffect(() => {
    if (dataset && schema?.mode === 'qa' && !qualityMetrics) {
      calculateBasicQualityMetrics();
    }
  }, [dataset, schema?.mode, qualityMetrics, calculateBasicQualityMetrics]);

  // Auto-select all documents when moving to step 2 (Select Documents)
  useEffect(() => {
    if (currentStep === 2 && documents.length > 0 && selectedDocuments.length === 0) {
      // Auto-select all documents for convenience
      setSelectedDocuments(documents.map(doc => doc.id));
    }
  }, [currentStep, documents, selectedDocuments.length]);
  const loadAllData = async () => {
    if (!projectId) return;
    
    setLoading(true);
    try {
      await Promise.all([
        loadProject(),
        loadDocuments(),
        loadSchema(),
        loadDataset(),
        loadProcessingJobs()
      ]);
    } finally {
      setLoading(false);
    }
  };

  const loadProject = async () => {
    if (!projectId) return;
    
    setLoading(true); // Set loading to true when starting
    try {
      const projectData = await documentApi.getProject(projectId);
      setProject(projectData);
    } catch (error: any) {
      console.error('Error loading project:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to load project",
        variant: "destructive"
      });
      navigate('/dashboard');
    } finally {
      setLoading(false); // Always set loading to false when done
    }
  };

  const loadDocuments = async () => {
    if (!projectId) return;
    
    setLoadingDocuments(true);
    try {
      const docs = await documentApi.getProjectDocuments(projectId);
      setDocuments(docs);
    } catch (error: any) {
      console.error('Error loading documents:', error);
    } finally {
      setLoadingDocuments(false);
    }
  };

  const loadSchema = async () => {
    if (!projectId) return;
    
    try {
      const schemaData = await documentApi.getProjectSchema(projectId);
      setSchema(schemaData);
      // Initialize builder fields from schema if present
      const gen = schemaData?.schema?.generated_schema as any[] | undefined;
      if (gen && Array.isArray(gen)) {
        const converted = gen.map(f => ({
          key: f.key,
          type: (f.type || 'string') as SchemaFieldInput['type'],
          required: !!f.required,
          description: f.description || ''
        }));
        setEditingFields(converted);
        setSchemaDirty(false);
      } else {
        setEditingFields([]);
      }
    } catch (error: any) {
      console.error('Error loading schema:', error);
    }
  };

  const loadDataset = async () => {
    if (!projectId) return;
    
    try {
      const datasetData = await documentApi.getProjectDataset(projectId);
      setDataset(datasetData);
    } catch (error: any) {
      console.error('Error loading dataset:', error);
    }
  };

  const loadUserProfile = async () => {
    try {
      const profile = await documentApi.getUserProfile();
      setUserProfile(profile);
    } catch (error) {
      console.error('Error loading user profile:', error);
      // Set default profile for free tier
      setUserProfile({ subscription_tier: 'free' });
    }
  };

  const loadProcessingJobs = async () => {
    if (!projectId) return;
    
    try {
      const jobs = await documentApi.getProjectJobs(projectId);
      setProcessingJobs(jobs);
      
      // Check if there's an active task
      const runningJob = jobs.find(job => job.status === 'running' || job.status === 'pending');
      if (runningJob) {
        try {
          const taskStatus = await documentApi.getTaskStatus(runningJob.id);
          setActiveTask(taskStatus);
        } catch (error) {
          console.error('Error getting task status:', error);
        }
      }
    } catch (error: any) {
      console.error('Error loading processing jobs:', error);
    }
  };

  const generateQualityAnalysis = async () => {
    if (!dataset || !schema || schema.mode !== 'qa') {
      toast({
        title: "Quality Analysis Not Available",
        description: "Quality analysis is only available for Q&A datasets",
        variant: "destructive"
      });
      return;
    }

    setQualityAnalysisLoading(true);
    try {
      // Convert dataset records to QARecord format
      const qaRecords: QARecord[] = dataset.records.map(record => ({
        question: record.question || '',
        answer: record.answer || '',
        context: record.context || '',
        difficulty: record.difficulty || '',
        topic: record.topic || '',
        question_type: record.question_type || '',
        explanation: record.explanation || '',
        keywords: record.keywords || '',
        ...record // Include any additional fields
      }));

      // Calculate quality metrics (this updates both Step 4 and Step 5)
      const metrics = calculateQAQualityMetrics(qaRecords);
      setQualityMetrics(metrics);

      toast({
        title: "Detailed Quality Report Generated",
        description: `Detailed analysis complete! Navigate to Step 5 to view comprehensive quality insights.`,
      });
    } catch (error) {
      console.error('Error generating quality analysis:', error);
      toast({
        title: "Quality Analysis Failed",
        description: "Failed to generate detailed quality report. Basic quality score is still available.",
        variant: "destructive"
      });
    } finally {
      setQualityAnalysisLoading(false);
    }
  };

  const handleUploadComplete = (response: UploadResponse) => {
    toast({
      title: "Upload Complete",
      description: `${response.total_uploaded} files uploaded successfully`,
    });
    
    // Only reload documents list (more efficient)
    loadDocuments();
    
    // Clear selected files after successful upload
    setSelectedFiles([]);
    
    // Update project status only if needed (avoid unnecessary API call)
    if (project?.status === 'created') {
      loadProject();
    }
    
    // Mark step 2 as accessible and advance to it
    setCompletedSteps(prev => new Set([...Array.from(prev), 2]));
    setCurrentStep(2);
  };

  const handleDeleteDocument = (documentId: string, filename: string) => {
    if (!projectId) return;
    setDocToDelete({ id: documentId, filename });
    setShowDeleteDocDialog(true);
  };

  const confirmDeleteDocument = async () => {
    if (!projectId || !docToDelete) return;
    
    try {
      await documentApi.deleteDocument(projectId, docToDelete.id);
      
      toast({
        title: "Document Deleted",
        description: `"${docToDelete.filename}" has been deleted successfully`,
        variant: "default"
      });
      
      // Refresh documents list
      loadDocuments();
      
    } catch (error: any) {
      console.error('Error deleting document:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to delete document",
        variant: "destructive"
      });
    } finally {
      setShowDeleteDocDialog(false);
      setDocToDelete(null);
    }
  };

  const handleGenerateSchema = async (customInstruction?: string, mode: 'business' | 'qa' = 'business') => {
    if (!projectId) return;
    
    if (documents.length === 0) {
      toast({
        title: "No Documents",
        description: "Please upload documents before generating schema",
        variant: "destructive"
      });
      return;
    }

    if (selectedDocuments.length === 0) {
      toast({
        title: "No Documents Selected",
        description: "Please select at least one document to generate schema from",
        variant: "destructive"
      });
      return;
    }

    setLoadingSchema(true);
    setIsGeneratingSchema(true);
    try {
      const result = await documentApi.generateSchema(projectId, customInstruction, mode, selectedDocuments);
      
      // Start polling for task status
      const taskStatus = await documentApi.getTaskStatus(result.task_id);
      setActiveTask(taskStatus);
      
      if (mode === 'qa') {
        toast({
          title: "Q&A Schema Generation Started",
          description: "AI is analyzing your selected documents to generate Q&A training pairs. You'll be able to preview and generate the full dataset once complete.",
        });
      } else {
        toast({
          title: "Schema Generation Started",
          description: "AI is analyzing your selected documents to generate a business dataset schema",
        });
      }
      
    } catch (error: any) {
      console.error('Error starting schema generation:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to start schema generation",
        variant: "destructive"
      });
    } finally {
      setLoadingSchema(false);
      setIsGeneratingSchema(false);
    }
  };

  // Schema Builder helpers
  const supportedTypes: SchemaFieldInput['type'][] = ['string', 'number', 'integer', 'boolean', 'date', 'datetime', 'enum'];

  const validateFields = (fields: SchemaFieldInput[]): string | null => {
    if (fields.length < 1 || fields.length > 100) return 'Schema must have between 1 and 100 fields.';
    const seen = new Set<string>();
    const keyRegex = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
    for (const f of fields) {
      const k = f.key.trim();
      if (k.length < 1 || k.length > 64) return `Invalid key length for "${f.key}"`;
      if (!keyRegex.test(k)) return `Invalid key: ${f.key}`;
      const lower = k.toLowerCase();
      if (seen.has(lower)) return `Duplicate key: ${f.key}`;
      seen.add(lower);
      if (!supportedTypes.includes(f.type)) return `Unsupported type for ${f.key}: ${f.type}`;
      if (f.description && f.description.length > 200) return `Description too long for ${f.key}`;
    }
    return null;
  };

  const addField = () => {
    const nextIndex = editingFields.length + 1;
    const newField: SchemaFieldInput = { key: `field_${nextIndex}`, type: 'string', required: false, description: '' };
    const updated = [...editingFields, newField];
    setEditingFields(updated);
    setSchemaDirty(true);
    setSchemaErrors(validateFields(updated));
  };

  const updateField = (index: number, patch: Partial<SchemaFieldInput>) => {
    const updated = editingFields.map((f, i) => (i === index ? { ...f, ...patch } : f));
    setEditingFields(updated);
    setSchemaDirty(true);
    setSchemaErrors(validateFields(updated));
  };

  const removeField = (index: number) => {
    const updated = editingFields.filter((_, i) => i !== index);
    setEditingFields(updated);
    setSchemaDirty(true);
    setSchemaErrors(validateFields(updated));
  };

  const saveSchema = async () => {
    if (!projectId) return;
    const err = validateFields(editingFields);
    if (err) {
      setSchemaErrors(err);
      toast({ title: 'Validation error', description: err, variant: 'destructive' });
      return;
    }
    try {
      const result = await documentApi.updateProjectSchema(projectId, {
        schema: { fields: editingFields },
        // do not send instruction unless user edits an instruction field (not in v1 UI yet)
      });
      setSchema((prev) => ({ ...(prev || {}), schema: result.schema } as Schema));
      setSchemaDirty(false);
      toast({ title: 'Schema saved', description: 'Your schema has been updated.' });
    } catch (e: any) {
      toast({ title: 'Save failed', description: e.message || 'Could not save schema', variant: 'destructive' });
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await documentApi.listSchemaTemplates(undefined, templateQuery || undefined);
      setTemplates(data);
    } catch (e) {
      // ignore silently
    }
  };

  const applyTemplate = async (templateId: string) => {
    if (!projectId) return;
    if (schemaDirty && !window.confirm('You have unsaved changes. Applying a template will replace the current schema. Continue?')) return;
    try {
      const res = await documentApi.applySchemaTemplate(projectId, templateId);
      // reflect in UI
      const gen = res.schema?.generated_schema as any[] | undefined;
      if (gen) {
        const converted = gen.map(f => ({
          key: f.key,
          type: (f.type || 'string') as SchemaFieldInput['type'],
          required: !!f.required,
          description: f.description || ''
        }));
        setEditingFields(converted);
        setSchema((prev) => ({ ...(prev || {}), schema: res.schema } as Schema));
        setSchemaDirty(false);
        toast({ title: 'Template applied', description: 'Schema replaced with selected template.' });
      }
    } catch (e: any) {
      toast({ title: 'Apply failed', description: e.message || 'Could not apply template', variant: 'destructive' });
    }
  };

  const handleGenerateDataset = async (numRecords: number = 10) => {
    if (!projectId) return;
    
    if (!schema) {
      toast({
        title: "No Schema",
        description: "Please generate schema first",
        variant: "destructive"
      });
      return;
    }

    setLoadingDataset(true);
    setIsGeneratingDataset(true);
    try {
      const result = await documentApi.generateDataset(projectId, numRecords);
      
      // Start polling for task status
      const taskStatus = await documentApi.getTaskStatus(result.task_id);
      setActiveTask(taskStatus);
      
      toast({
        title: "Dataset Generation Started",
        description: `AI is generating ${numRecords} records from your documents`,
      });
      
    } catch (error: any) {
      console.error('Error starting dataset generation:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to start dataset generation",
        variant: "destructive"
      });
    } finally {
      setLoadingDataset(false);
      setIsGeneratingDataset(false);
    }
  };

  const handleStepClick = (step: number) => {
    // Allow navigation to:
    // 1. Any step that has been unlocked (in completedSteps), OR
    // 2. Any step up to and including current step (allows backward navigation)
    const isAccessible = completedSteps.has(step) || step <= currentStep;
    
    if (!isAccessible) {
      toast({
        title: "Step Not Accessible",
        description: `Please complete the previous steps first before accessing step ${step}`,
        variant: "destructive"
      });
      return;
    }
    
    setManualNavigation(true); // Set flag to prevent auto-advancement
    setCurrentStep(step);
    
    // Load data if needed when navigating to specific steps
    switch (step) {
      case 3:
        if (!schema) {
          loadSchema();
          loadProcessingJobs();
        }
        break;
      case 4:
        if (!dataset) {
          loadDataset();
        }
        break;
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      'created': { color: 'bg-gray-100 text-gray-800', icon: Clock },
      'documents_uploaded': { color: 'bg-blue-100 text-blue-800', icon: Upload },
      'processing': { color: 'bg-yellow-100 text-yellow-800', icon: Loader2 },
      'schema_generated': { color: 'bg-purple-100 text-purple-800', icon: Settings },
      'completed': { color: 'bg-green-100 text-green-800', icon: CheckCircle },
      'error': { color: 'bg-red-100 text-red-800', icon: AlertCircle }
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.created;
    const IconComponent = config.icon;
    
    return (
      <Badge className={config.color}>
        <IconComponent className="h-3 w-3 mr-1" />
        {status.replace('_', ' ').toUpperCase()}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading project...</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Project not found</p>
          <Button onClick={() => navigate('/dashboard')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  // Helper function for recommended records
  const getRecommendedRecords = () => {
    const totalPages = documents.reduce((sum, doc) => sum + (doc.page_count || 0), 0);
    const totalDocuments = documents.length;
    
    // Base recommendation: 2-5 records per page depending on content type
    let baseRecommendation = totalPages * 3;
    
    // Adjust based on document count (more documents = more variety)
    if (totalDocuments > 1) {
      baseRecommendation += totalDocuments * 5; // Bonus for multiple documents
    }
    
    // Cap by tier limits
    const tierLimit = userProfile?.subscription_tier === 'enterprise' ? 5000 : 
                     userProfile?.subscription_tier === 'paid' ? 500 : 50;
    
    return Math.min(baseRecommendation, tierLimit);
  };

  const getTotalPages = (docs: Document[]) => {
    return docs.reduce((sum, doc) => {
      // Try page_count first, fallback to pages_extracted
      const pages = doc.page_count || doc.pages_extracted || 0;
      return sum + pages;
    }, 0);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <Button 
              variant="outline" 
              onClick={() => navigate('/dashboard')}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{project.name}</h1>
              {project.description && (
                <p className="text-gray-600 mt-1">{project.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {/* {getStatusBadge(project.status)} */}
            <Button variant="outline">
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>

        {/* Project Info Card */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <p className="text-sm font-medium text-gray-600">Created</p>
                <p className="text-lg font-semibold text-gray-900">
                  {new Date(project.created_at).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Last Updated</p>
                <p className="text-lg font-semibold text-gray-900">
                  {new Date(project.updated_at).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">Documents</p>
                <p className="text-lg font-semibold text-gray-900">
                  {documents.length}
                </p>
              </div>
            </div>
            
            {project.instruction && (
              <div className="mt-6">
                <p className="text-sm font-medium text-gray-600 mb-2">Processing Instructions</p>
                <p className="text-gray-900 bg-gray-50 p-3 rounded-lg">
                  {project.instruction}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Progress Indicator */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
            {[
            { step: 1, label: "Upload Documents", icon: Upload },
            { step: 2, label: "Generate Schema", icon: Settings },
            { step: 3, label: "Dataset Preview", icon: FileText },
            { step: 4, label: "Export Dataset", icon: Download },
            { step: 5, label: "Data Quality", icon: CheckCircle }
          ].map(({ step, label, icon: Icon }, index) => {
            const isCompleted = currentStep > step;
            const isCurrent = currentStep === step;
            const isAccessible = completedSteps.has(step) || step <= currentStep;
            
            return (
              <div key={step} className="flex items-center">
                <div 
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                    isAccessible 
                      ? 'cursor-pointer' 
                      : 'cursor-not-allowed opacity-50'
                  } ${
                    isCurrent 
                      ? 'bg-blue-100 text-blue-700 font-semibold' 
                      : isCompleted 
                        ? 'bg-green-100 text-green-700 hover:bg-green-200' 
                        : isAccessible
                          ? 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                          : 'bg-gray-100 text-gray-400'
                  }`}
                  onClick={() => isAccessible && handleStepClick(step)}
                >
                  <div className={`flex items-center justify-center w-6 h-6 rounded-full ${
                    isCompleted 
                      ? 'bg-green-600 text-white' 
                      : isCurrent 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-300 text-gray-600'
                  }`}>
                    {isCompleted ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <span className="text-xs font-semibold">{step}</span>
                    )}
                  </div>
                  <Icon className="w-4 h-4" />
                  <span className="text-sm">{label}</span>
                </div>
                {index < 4 && (
                  <div className={`w-8 h-0.5 mx-2 ${
                    isCompleted ? 'bg-green-600' : 'bg-gray-300'
                  }`} />
                )}
              </div>
            );
          })}
            </div>
          </CardContent>
        </Card>

        {/* Step Content */}
        <div className="space-y-6">
          {/* Step 1: Upload Documents */}
          {currentStep === 1 && (
            <Card>
              <CardHeader>
                <CardTitle>Upload Documents</CardTitle>
              </CardHeader>
              <CardContent>
                <FileUpload
                  projectId={project.id}
                  files={selectedFiles}
                  setFiles={setSelectedFiles}
                  onUploadComplete={handleUploadComplete}
                  maxFiles={5}
                  maxFileSize={5}
                />
              </CardContent>
            </Card>
          )}

          {/* Step 2: Select Documents */}
          {currentStep === 2 && (
            <Card>
              <CardHeader>
                <CardTitle>Project Documents</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingDocuments ? (
                  <div className="text-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
                    <p className="text-gray-600">Loading documents...</p>
                  </div>
                ) : documents.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No documents yet</h3>
                    <p className="text-gray-600 mb-6">Upload documents to get started with processing.</p>
                    <Button onClick={() => setCurrentStep(1)}>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload Documents
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Generate Schema Button */}
                    {selectedDocuments.length > 0 && (
                      <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-blue-900">
                              {selectedDocuments.length} document{selectedDocuments.length > 1 ? 's' : ''} selected
                            </p>
                            <p className="text-sm text-blue-700">
                              Ready to generate schema from selected documents
                            </p>
                          </div>
                          <Button 
                            onClick={() => setInstructionOpen(true)}
                            disabled={isGeneratingSchema}
                            className="bg-blue-600 hover:bg-blue-700"
                          >
                            {isGeneratingSchema ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Generating...
                              </>
                            ) : (
                              <>
                                <Sparkles className="h-4 w-4 mr-2" />
                                Generate Schema
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    )}
                    
                    {documents.map((doc) => (
                      <div key={doc.id} className={`border rounded-lg p-4 transition-colors ${
                        selectedDocuments.includes(doc.id) 
                          ? 'bg-blue-50 border-blue-200' 
                          : 'hover:bg-gray-50'
                      }`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3 flex-1">
                            <input
                              type="checkbox"
                              checked={selectedDocuments.includes(doc.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setSelectedDocuments([...selectedDocuments, doc.id]);
                                } else {
                                  setSelectedDocuments(selectedDocuments.filter(id => id !== doc.id));
                                }
                              }}
                              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                              disabled={isGeneratingSchema}
                            />
                            <div className="flex-1">
                              <h3 className="font-semibold text-lg">{doc.filename}</h3>
                              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                                <span>Size: {(doc.file_size / (1024 * 1024)).toFixed(1)} MB</span>
                                <span>Pages: {doc.pages_extracted || 0}</span>
                                <span>Type: {doc.file_type}</span>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {getStatusBadge(doc.status)}
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              disabled={isGeneratingSchema}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Step 3: Schema */}
          {currentStep === 3 && (
            <>
              {/* Active Task Progress */}
              {activeTask && (activeTask.task_type === 'schema_generation' || activeTask.task_type === 'dataset_generation') && (
                <Card className="border-blue-200 bg-blue-50">
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-4">
                      <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
                      <div className="flex-1">
                        <p className="font-medium text-blue-900">
                          {activeTask.task_type === 'schema_generation' ? 'Generating Schema...' : 'Generating Dataset...'}
                        </p>
                        <p className="text-sm text-blue-700">{activeTask.message}</p>
                        <div className="mt-2">
                          <div className="w-full bg-blue-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                              style={{ width: `${activeTask.progress}%` }}
                            ></div>
                          </div>
                          <p className="text-xs text-blue-600 mt-1">{activeTask.progress}% complete</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle>Data Schema</CardTitle>
                    <Button 
                      onClick={() => setInstructionOpen(true)}
                      disabled={loadingSchema || documents.length === 0 || (activeTask?.status === 'running')}
                    >
                      {loadingSchema ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-4 w-4 mr-2" />
                          {schema ? 'Regenerate Schema' : 'Generate Schema'}
                        </>
                      )}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {!schema ? (
                    <div className="text-center py-12">
                      <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No Schema Generated</h3>
                      <p className="text-gray-600 mb-6">
                        {documents.length === 0 
                          ? 'Upload documents first to generate a data schema.'
                          : 'Click "Generate Schema" to analyze your documents and create a data structure.'
                        }
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-2">Schema Information</h4>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-gray-600">Mode:</span>
                            <span className="ml-2 font-medium">
                              {schema.mode === 'business' ? '🏢 Business Dataset' : '🧠 Q&A Training'}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">Status:</span>
                            <span className="ml-2 font-medium">{schema.status}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">Generated from:</span>
                            <span className="ml-2 font-medium">{schema.generated_from} documents</span>
                          </div>
                          <div>
                            <span className="text-gray-600">Created:</span>
                            <span className="ml-2 font-medium">
                              {schema.created_at ? new Date(schema.created_at).toLocaleDateString() : 'N/A'}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">Updated:</span>
                            <span className="ml-2 font-medium">
                              {schema.updated_at ? new Date(schema.updated_at).toLocaleDateString() : 'N/A'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {schema.instruction && (
                        <div className="bg-blue-50 p-4 rounded-lg">
                          <h4 className="font-medium text-blue-900 mb-2">Processing Instructions</h4>
                          <p className="text-blue-800 text-sm">{schema.instruction.split('\n\nAdditional Instructions: ')[1]}</p>
                        </div>
                      )}

                      {/* Q&A Mode - Show Preview and Dataset Generation */}
                      {schema.mode === 'qa' && (
                        <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                          <h4 className="font-medium text-green-900 mb-3">🧠 Q&A Training Data Ready!</h4>
                          <p className="text-green-800 text-sm mb-4">
                            Your Q&A schema has been generated successfully. You can now preview sample Q&A pairs and generate the full training dataset.
                          </p>
                          <div className="flex flex-wrap gap-3">
                            <Button 
                              onClick={async () => {
                                if (!projectId || !schema) return;
                                setPreviewLoading(true);
                                setPreviewData(null);
                                try {
                                  const res = await documentApi.generateSchemaPreview(projectId, { num_records: 5, chunk_strategy: 'top', temperature: 0.4 });
                                  setPreviewData(res);
                                } catch (e: any) {
                                  toast({ title: 'Preview failed', description: e.message || 'Could not generate preview', variant: 'destructive' });
                                } finally {
                                  setPreviewLoading(false);
                                }
                              }}
                              disabled={previewLoading || documents.length === 0}
                              className="bg-green-600 hover:bg-green-700"
                            >
                              {previewLoading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin"/>Generating Preview...</> : <>Generate Sample Preview</>}
                            </Button>
                            <Button 
                              variant="outline"
                              onClick={() => setDatasetDialogOpen(true)}
                              disabled={loadingDataset || (activeTask?.status === 'running')}
                              className="border-green-300 text-green-700 hover:bg-green-50"
                            >
                              {loadingDataset ? <><Loader2 className="h-4 w-4 mr-2 animate-spin"/>Starting...</> : <>Generate Full Q&A Dataset</>}
                            </Button>
                          </div>
                        </div>
                      )}

                    {/* Schema Builder - Only show for Business mode */}
                    {schema.mode === 'business' && (
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-medium text-gray-900">Schema Builder</h4>
                          <div className="space-x-2">
                            <Button variant="outline" onClick={addField}>Add Field</Button>
                            <Dialog open={templateDrawerOpen} onOpenChange={(o) => { setTemplateDrawerOpen(o); if (o) loadTemplates(); }}>
                              <DialogTrigger asChild>
                                <Button variant="outline">Templates</Button>
                              </DialogTrigger>
                              <DialogContent className="max-w-2xl">
                                <DialogHeader>
                                  <DialogTitle>Apply Schema Template</DialogTitle>
                                </DialogHeader>
                                <div className="space-y-4">
                                  <Input placeholder="Search templates" value={templateQuery} onChange={(e) => setTemplateQuery(e.target.value)} />
                                  <Button variant="outline" onClick={loadTemplates}>Search</Button>
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-96 overflow-auto">
                                    {(templates?.builtin || []).map(t => (
                                      <div key={t.id} className="border rounded p-3">
                                        <div className="text-xs text-gray-500 mb-1">Built-in</div>
                                        <div className="font-medium">{t.name}</div>
                                        {t.description && <div className="text-sm text-gray-600">{t.description}</div>}
                                        <Button className="mt-2" size="sm" onClick={() => applyTemplate(t.id)}>Apply</Button>
                                      </div>
                                    ))}
                                    {(templates?.mine || []).map(t => (
                                      <div key={t.id} className="border rounded p-3">
                                        <div className="text-xs text-gray-500 mb-1">My Template</div>
                                        <div className="font-medium">{t.name}</div>
                                        {t.description && <div className="text-sm text-gray-600">{t.description}</div>}
                                        <Button className="mt-2" size="sm" onClick={() => applyTemplate(t.id)}>Apply</Button>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              </DialogContent>
                            </Dialog>
                            <Button onClick={saveSchema} disabled={!!schemaErrors || !schemaDirty}>Save</Button>
                            <Button variant="outline" onClick={() => setSaveTemplateOpen(true)}>Save as Template</Button>
                          </div>
                        </div>

                        {schemaErrors && (
                          <div className="text-sm text-red-600 mb-2">{schemaErrors}</div>
                        )}

                        <div className="space-y-3">
                          {editingFields.length === 0 && (
                            <div className="text-sm text-gray-600">No fields yet. Click "Add Field" to start.</div>
                          )}
                          {editingFields.map((f, idx) => (
                            <div key={idx} className="grid grid-cols-1 md:grid-cols-12 gap-2 items-center border rounded p-3">
                              <div className="md:col-span-3">
                                <Input value={f.key} onChange={(e) => updateField(idx, { key: e.target.value })} placeholder="key" />
                              </div>
                              <div className="md:col-span-3">
                                <Select value={f.type} onValueChange={(v) => updateField(idx, { type: v as SchemaFieldInput['type'] })}>
                                  <SelectTrigger>
                                    <SelectValue placeholder="Type" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {supportedTypes.map(t => (
                                      <SelectItem key={t} value={t}>{t}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="md:col-span-2">
                                <label className="inline-flex items-center space-x-2 text-sm text-gray-700">
                                  <input type="checkbox" checked={!!f.required} onChange={(e) => updateField(idx, { required: e.target.checked })} />
                                  <span>Required</span>
                                </label>
                              </div>
                              <div className="md:col-span-3">
                                <Input value={f.description || ''} onChange={(e) => updateField(idx, { description: e.target.value })} placeholder="description (≤ 200 chars)" />
                              </div>
                              <div className="md:col-span-1 flex justify-end">
                                <Button variant="outline" className="text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => removeField(idx)}>Remove</Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Business Mode - Show Schema Builder Controls */}
                    {schema.mode === 'business' && (
                      <div className="flex justify-center">
                        <div className="flex flex-col items-center gap-4 w-full">
                          <TooltipProvider>
                          <div className="flex flex-wrap items-center gap-3">
                            {/* Count with embedded info icon */}
                            <div className="relative inline-flex items-center">
                              <Input type="number" min={1} max={10} className="w-24 pr-8" value={previewCount} onChange={(e) => setPreviewCount(Math.max(1, Math.min(10, Number(e.target.value) || 1)))} />
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700">
                                    <Info className="h-4 w-4" />
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Number of rows to preview (1–10). Default 5.</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>

                            {/* Strategy select with embedded info */}
                            <div className="relative inline-flex items-center">
                              <Select value={previewStrategy} onValueChange={(v) => setPreviewStrategy(v as 'top'|'random')}>
                                <SelectTrigger className="w-36 pr-8"><SelectValue placeholder="Strategy" /></SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="top">Top</SelectItem>
                                  <SelectItem value="random">Random</SelectItem>
                                </SelectContent>
                              </Select>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700">
                                    <Info className="h-4 w-4" />
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Top = first chunks by order; Random = random selection.</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>

                            {/* Temperature with embedded info */}
                            <div className="relative inline-flex items-center">
                              <Input type="number" step="0.1" min={0} max={1} className="w-28 pr-8" value={previewTemp} onChange={(e) => setPreviewTemp(Math.max(0, Math.min(1, Number(e.target.value) || 0)))} />
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700">
                                    <Info className="h-4 w-4" />
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Temperature (0–1). Higher = more diverse output. Default 0.4.</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            <Button 
                              onClick={async () => {
                                if (!projectId || !schema) return;
                                setPreviewLoading(true);
                                setPreviewData(null);
                                try {
                                  const res = await documentApi.generateSchemaPreview(projectId, { num_records: previewCount, chunk_strategy: previewStrategy, temperature: previewTemp });
                                  setPreviewData(res);
                                } catch (e: any) {
                                  toast({ title: 'Preview failed', description: e.message || 'Could not generate preview', variant: 'destructive' });
                                } finally {
                                  setPreviewLoading(false);
                                }
                              }}
                              disabled={previewLoading || documents.length === 0}
                            >
                              {previewLoading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin"/>Generating...</> : <>Generate sample preview</>}
                            </Button>
                            <Button 
                              variant="outline"
                              onClick={() => handleGenerateDataset(5)}
                              disabled={loadingDataset || (activeTask?.status === 'running')}
                            >
                              {loadingDataset ? <><Loader2 className="h-4 w-4 mr-2 animate-spin"/>Starting...</> : <>Generate Sample Dataset</>}
                            </Button>
                          </div>
                          </TooltipProvider>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Preview Data Display - Show for both modes */}
                {previewData && (
                  <div className="w-full mt-6">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-sm text-gray-700">Validation: {previewData.validation.summary.valid}/{previewData.validation.summary.total} rows valid ({previewData.validation.summary.invalid} invalid)</div>
                      <div className="space-x-2">
                        <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(JSON.stringify(previewData.records, null, 2))}>Copy JSON</Button>
                        <Button variant="outline" size="sm" onClick={() => {
                          const csv = (() => {
                            if (!previewData.records.length) return '';
                            const headers = Object.keys(previewData.records[0]);
                            const rows = previewData.records.map(r => headers.map(h => JSON.stringify(r[h] ?? '')).join(','));
                            return [headers.join(','), ...rows].join('\n');
                          })();
                          const blob = new Blob([csv], { type: 'text/csv' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url; a.download = 'preview.csv'; a.click(); URL.revokeObjectURL(url);
                        }}>Copy CSV</Button>
                        <Button variant="outline" size="sm" onClick={() => {
                          // trigger regenerate with same params
                          (async () => {
                            if (!projectId) return;
                            setPreviewLoading(true);
                            try {
                              const res = await documentApi.generateSchemaPreview(projectId, { num_records: previewCount, chunk_strategy: previewStrategy, temperature: previewTemp });
                              setPreviewData(res);
                            } finally { setPreviewLoading(false); }
                          })();
                        }}>Regenerate</Button>
                      </div>
                    </div>
                    <div className="border rounded-lg overflow-x-auto">
                      {previewData.records.length > 0 && (
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              {Object.keys(previewData.records[0]).map((key) => (
                                <th key={key} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{key}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {previewData.records.map((row, rIdx) => (
                              <tr key={rIdx}>
                                {Object.entries(row).map(([k, v], cIdx) => {
                                  const cellIssues = previewData.validation.issues.filter(i => i.row === rIdx+1 && i.field === k);
                                  const invalid = cellIssues.length > 0;
                                  return (
                                    <td key={cIdx} className={`px-4 py-2 whitespace-nowrap text-sm ${invalid ? 'bg-red-50 text-red-700' : 'text-gray-900'}`} title={invalid ? cellIssues.map(i => i.message).join('; ') : ''}>
                                      {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
            </>
          )}

          {/* Step 4: Export Dataset */}
          {currentStep === 4 && (
            <Card>
              <CardHeader>
                <CardTitle>Generated Dataset</CardTitle>
              </CardHeader>
              <CardContent>
                {!dataset ? (
                  <div className="text-center py-12">
                    <Download className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Dataset Generated</h3>
                    <p className="text-gray-600 mb-6">Generate a dataset first to export data.</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Quality Overview for Q&A datasets */}
                    {schema?.mode === 'qa' && (
                      <div className="bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg p-6">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <h3 className="text-xl font-semibold text-gray-900">Overall Quality Score</h3>
                            <p className="text-gray-600">Comprehensive analysis of your Q&A dataset</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {qualityMetrics ? (
                              <div className="text-right">
                                <div className="text-4xl font-bold text-blue-600">
                                  {qualityMetrics.quality_score.overall_score}/100
                                </div>
                                <div className="text-sm text-gray-600">
                                  {qualityMetrics.quality_score.overall_score >= 90 ? 'Excellent' :
                                   qualityMetrics.quality_score.overall_score >= 80 ? 'Great' :
                                   qualityMetrics.quality_score.overall_score >= 70 ? 'Good' :
                                   qualityMetrics.quality_score.overall_score >= 60 ? 'Fair' : 'Needs Improvement'}
                                </div>
                              </div>
                            ) : (
                              <div className="text-right">
                                <div className="text-4xl font-bold text-gray-400">
                                  --/100
                                </div>
                                <div className="text-sm text-gray-500">Calculating...</div>
                              </div>
                            )}
                          </div>
                        </div>
                        
                        {qualityMetrics && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="text-center p-3 bg-white rounded-lg border">
                              <div className="text-2xl font-bold text-blue-600">
                                {qualityMetrics.total_qa_pairs}
                              </div>
                              <div className="text-sm text-gray-600">Total Q&A</div>
                            </div>
                            <div className="text-center p-3 bg-white rounded-lg border">
                              <div className="text-2xl font-bold text-green-600">
                                {qualityMetrics.quality_score.breakdown.completeness}%
                              </div>
                              <div className="text-sm text-gray-600">Completeness</div>
                            </div>
                            <div className="text-center p-3 bg-white rounded-lg border">
                              <div className="text-2xl font-bold text-purple-600">
                                {qualityMetrics.schema_coverage.coverage_percentage}%
                              </div>
                              <div className="text-sm text-gray-600">Schema Coverage</div>
                            </div>
                            <div className="text-center p-3 bg-white rounded-lg border">
                              <div className="text-2xl font-bold text-orange-600">
                                {qualityMetrics.grounding_metrics.avg_grounding_score}%
                              </div>
                              <div className="text-sm text-gray-600">Avg Grounding</div>
                            </div>
                          </div>
                        )}
                        
                        {/* Generate Quality Report Button */}
                        <div className="mt-4 flex justify-end">
                          <Button 
                            onClick={generateQualityAnalysis}
                            disabled={qualityAnalysisLoading}
                            className="bg-blue-600 hover:bg-blue-700"
                          >
                            {qualityAnalysisLoading ? (
                              <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Generating Detailed Report...
                              </>
                            ) : (
                              <>
                                <CheckCircle className="h-4 w-4 mr-2" />
                                Generate Detailed Quality Report
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    )}

                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">Dataset Records</h3>
                        <p className="text-gray-600">
                          Showing {dataset.records.length} of {dataset.total_records} records
                        </p>
                      </div>
                      <div className="space-x-2">
                        <Button 
                          variant="outline"
                          onClick={() => {
                            const csvContent = convertToCSV(dataset.records);
                            downloadFile(csvContent, `${project?.name || 'dataset'}.csv`, 'text/csv');
                          }}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Export CSV
                        </Button>
                        <Button 
                          variant="outline"
                          onClick={() => {
                            const jsonContent = JSON.stringify(dataset.records, null, 2);
                            downloadFile(jsonContent, `${project?.name || 'dataset'}.json`, 'application/json');
                          }}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Export JSON
                        </Button>
                      </div>
                    </div>

                    {/* Dataset Preview */}
                    <div className="border rounded-lg overflow-hidden">
                      <div className="bg-gray-50 px-4 py-2 border-b">
                        <h4 className="font-medium text-gray-900">Data Preview</h4>
                      </div>
                      <div className="overflow-x-auto">
                        {dataset.records.length > 0 && (() => {
                          const orderedKeys = getOrderedKeys(dataset.records);
                          return (
                            <table className="min-w-full divide-y divide-gray-200">
                              <thead className="bg-gray-50">
                                <tr>
                                  {orderedKeys.map((key) => (
                                    <th key={key} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                      {key}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="bg-white divide-y divide-gray-200">
                                {dataset.records.slice(0, 10).map((record, index) => (
                                  <tr key={index}>
                                    {orderedKeys.map((key) => (
                                      <td key={key} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {typeof record[key] === 'object' ? JSON.stringify(record[key]) : String(record[key])}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          );
                        })()}
                      </div>
                      {dataset.total_records > 10 && (
                        <div className="bg-gray-50 px-4 py-2 border-t text-center text-sm text-gray-600">
                          Showing first 10 records. Export to see all {dataset.total_records} records.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>


            {/* Instruction Dialog */}
            <Dialog open={instructionOpen} onOpenChange={setInstructionOpen}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>AI Schema Generation</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  {/* Mode Selection */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">Generation Mode</label>
                    <div className="grid grid-cols-2 gap-3">
                      <div className={`border-2 rounded-lg p-4 cursor-pointer transition-colors ${
                        schemaMode === 'business' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                      }`} onClick={() => setSchemaMode('business')}>
                        <div className="flex items-center space-x-2">
                          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                          <input type="radio" name="mode" value="business" checked={schemaMode === 'business'} onChange={() => setSchemaMode('business')} className="sr-only" />
                          <div>
                            <div className="font-medium text-gray-900">🏢 Business Dataset</div>
                            <div className="text-xs text-gray-600">Generate structured business data (financials, invoices, contracts, etc.)</div>
                          </div>
                        </div>
                      </div>
                      <div className={`border-2 rounded-lg p-4 cursor-pointer transition-colors ${
                        schemaMode === 'qa' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                      }`} onClick={() => setSchemaMode('qa')}>
                        <div className="flex items-center space-x-2">
                          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                          <input type="radio" name="mode" value="qa" checked={schemaMode === 'qa'} onChange={() => setSchemaMode('qa')} className="sr-only" />
                          <div>
                            <div className="font-medium text-gray-900">🧠 Q&A Training</div>
                            <div className="text-xs text-gray-600">Generate question-answer pairs for AI model training</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Instructions */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">AI Instructions (Optional)</label>
                    <p className="text-sm text-gray-600 mb-2">
                      {schemaMode === 'business' 
                        ? 'Guide the AI to focus on specific business aspects (e.g., "Focus on financial statements; include revenue, expenses, assets")'
                        : 'Guide the AI to focus on specific Q&A aspects (e.g., "Focus on technical concepts; include difficulty levels")'
                      }
                    </p>
                    <Textarea 
                      value={instructionText} 
                      onChange={(e) => setInstructionText(e.target.value)} 
                      placeholder={
                        schemaMode === 'business'
                          ? "e.g., Focus on financial statements; include entity_name, fiscal_period, currency, revenue, expenses, net_income."
                          : "e.g., Focus on technical concepts; include difficulty levels and context information."
                      }
                    />
                  </div>

                  <div className="flex justify-end space-x-2 pt-2">
                    <Button variant="outline" onClick={() => setInstructionOpen(false)}>Cancel</Button>
                    <Button onClick={async () => {
                      setInstructionOpen(false);
                      await handleGenerateSchema(instructionText.trim() || undefined, schemaMode);
                      setInstructionText('');
                    }}>Start Generation</Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            {/* Save Template Dialog */}
            <Dialog open={saveTemplateOpen} onOpenChange={setSaveTemplateOpen}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Save Schema as Template</DialogTitle>
                </DialogHeader>
                <div className="space-y-3">
                  <Input placeholder="Template name" value={templateName} onChange={(e) => setTemplateName(e.target.value)} />
                  <Input placeholder="Category (optional)" value={templateCategory} onChange={(e) => setTemplateCategory(e.target.value)} />
                  <Textarea placeholder="Description (optional)" value={templateDescription} onChange={(e) => setTemplateDescription(e.target.value)} />
                  <div className="flex justify-end space-x-2 pt-2">
                    <Button variant="outline" onClick={() => setSaveTemplateOpen(false)}>Cancel</Button>
                    <Button onClick={async () => {
                      if (!schema?.schema) {
                        toast({ title: 'No schema', description: 'Generate or edit a schema first.' });
                        return;
                      }
                      if (!templateName.trim()) {
                        toast({ title: 'Name required', description: 'Please enter a template name.', variant: 'destructive' });
                        return;
                      }
                      try {
                        await documentApi.createSchemaTemplate({
                          name: templateName.trim(),
                          category: templateCategory.trim() || undefined,
                          description: templateDescription.trim() || undefined,
                          schema_json: schema.schema
                        });
                        setSaveTemplateOpen(false);
                        setTemplateName('');
                        setTemplateCategory('');
                        setTemplateDescription('');
                        toast({ title: 'Template saved', description: 'You can reuse it from Templates.' });
                      } catch (e: any) {
                        toast({ title: 'Save failed', description: e.message || 'Could not save template', variant: 'destructive' });
                      }
                    }}>Save</Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

          {/* Step 5: Data Quality */}
          {currentStep === 5 && (
            <Card>
              <CardHeader>
                <CardTitle>Data Quality Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                {!dataset || schema?.mode !== 'qa' ? (
                  <div className="text-center py-12">
                    <CheckCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Quality Analysis Not Available</h3>
                    <p className="text-gray-600 mb-6">Quality analysis is only available for Q&A datasets.</p>
                  </div>
                ) : !qualityMetrics ? (
                  <div className="text-center py-12">
                    <CheckCircle className="h-12 w-12 text-blue-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Generate Quality Analysis</h3>
                    <p className="text-gray-600 mb-6">Click the button below to analyze your Q&A dataset quality.</p>
                    <Button 
                      onClick={generateQualityAnalysis}
                      disabled={qualityAnalysisLoading}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {qualityAnalysisLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Analyzing Dataset...
                        </>
                      ) : (
                        <>
                          <CheckCircle className="h-4 w-4 mr-2" />
                          Analyze Dataset Quality
                        </>
                      )}
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Overall Quality Score */}
                    <div className="bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-xl font-semibold text-gray-900">Overall Quality Score</h3>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Info className="h-4 w-4 text-gray-400 hover:text-gray-600 cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs">
                                <p className="text-sm">
                                  <strong>Overall Quality Score (0-100):</strong> Weighted average of four key metrics:
                                  <br />• Completeness (25%): % of required fields filled
                                  <br />• Structure (25%): % of properly formatted records
                                  <br />• Grounding (25%): How well answers align with source context
                                  <br />• Schema Coverage (25%): % of schema fields utilized
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                          <p className="text-gray-600">Comprehensive analysis of your Q&A dataset</p>
                        </div>
                        <div className="text-right">
                          <div className="text-4xl font-bold text-blue-600">
                            {qualityMetrics.quality_score.overall_score}/100
                          </div>
                          <div className="text-sm text-gray-600">
                            {qualityMetrics.quality_score.overall_score >= 90 ? 'Excellent' :
                             qualityMetrics.quality_score.overall_score >= 80 ? 'Great' :
                             qualityMetrics.quality_score.overall_score >= 70 ? 'Good' :
                             qualityMetrics.quality_score.overall_score >= 60 ? 'Fair' : 'Needs Improvement'}
                          </div>
                        </div>
                      </div>
                      
                      {/* Quality Breakdown */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center p-3 bg-white rounded-lg border">
                          <div className="text-2xl font-bold text-green-600">
                            {qualityMetrics.quality_score.breakdown.completeness}%
                          </div>
                          <div className="text-sm text-gray-600">Completeness</div>
                        </div>
                        <div className="text-center p-3 bg-white rounded-lg border">
                          <div className="text-2xl font-bold text-blue-600">
                            {qualityMetrics.quality_score.breakdown.structure}%
                          </div>
                          <div className="text-sm text-gray-600">Structure</div>
                        </div>
                        <div className="text-center p-3 bg-white rounded-lg border">
                          <div className="text-2xl font-bold text-purple-600">
                            {qualityMetrics.quality_score.breakdown.grounding}%
                          </div>
                          <div className="text-sm text-gray-600">Grounding</div>
                        </div>
                        <div className="text-center p-3 bg-white rounded-lg border">
                          <div className="text-2xl font-bold text-orange-600">
                            {qualityMetrics.quality_score.breakdown.coverage}%
                          </div>
                          <div className="text-sm text-gray-600">Schema Coverage</div>
                        </div>
                      </div>
                    </div>

                    {/* Quality Assessment */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <h4 className="font-medium text-green-900 mb-2">Quality Assessment</h4>
                      <p className="text-green-800 text-sm">{qualityMetrics.quality_comments.overall_assessment}</p>
                    </div>

                    {/* Distribution Analysis */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* Difficulty Distribution */}
                      <div className="bg-white border rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Difficulty Distribution</h4>
                        <div className="space-y-2">
                          {Object.entries(qualityMetrics.difficulty_distribution).map(([level, count]) => (
                            <div key={level} className="flex items-center justify-between">
                              <span className="text-sm text-gray-600 capitalize">{level}</span>
                              <div className="flex items-center gap-2">
                                <div className="w-24 bg-gray-200 rounded-full h-2">
                                  <div 
                                    className="bg-blue-600 h-2 rounded-full" 
                                    style={{ width: `${(count / qualityMetrics.total_records) * 100}%` }}
                                  ></div>
                                </div>
                                <span className="text-sm font-medium w-8">{count}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Question Type Distribution */}
                      <div className="bg-white border rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Question Type Distribution</h4>
                        <div className="space-y-2">
                          {Object.entries(qualityMetrics.question_type_distribution).map(([type, count]) => (
                            <div key={type} className="flex items-center justify-between">
                              <span className="text-sm text-gray-600 capitalize">{type}</span>
                              <div className="flex items-center gap-2">
                                <div className="w-24 bg-gray-200 rounded-full h-2">
                                  <div 
                                    className="bg-green-600 h-2 rounded-full" 
                                    style={{ width: `${(count / qualityMetrics.total_records) * 100}%` }}
                                  ></div>
                                </div>
                                <span className="text-sm font-medium w-8">{count}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Topic Coverage */}
                    <div className="bg-white border rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 mb-3">Topic Coverage</h4>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm text-gray-600">
                          {qualityMetrics.topic_coverage.unique_topics} unique topics covered
                        </span>
                        <span className="text-sm font-medium text-blue-600">
                          {Object.keys(qualityMetrics.topic_coverage.topic_distribution).length} topic categories
                        </span>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                        {Object.entries(qualityMetrics.topic_coverage.topic_distribution)
                          .sort(([,a], [,b]) => b - a)
                          .slice(0, 8)
                          .map(([topic, count]) => (
                            <div key={topic} className="bg-gray-50 rounded p-2 text-center">
                              <div className="text-sm font-medium text-gray-900">{topic}</div>
                              <div className="text-xs text-gray-600">{count} records</div>
                            </div>
                          ))}
                      </div>
                    </div>

                    {/* Content Metrics */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="bg-white border rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Content Length Analysis</h4>
                        <div className="space-y-3">
                          <div>
                            <div className="text-sm text-gray-600 mb-1">Questions</div>
                            <div className="text-xs text-gray-500">
                              Avg: {qualityMetrics.content_metrics.question_length_stats.avg} chars
                              (Min: {qualityMetrics.content_metrics.question_length_stats.min}, 
                              Max: {qualityMetrics.content_metrics.question_length_stats.max})
                            </div>
                          </div>
                          <div>
                            <div className="text-sm text-gray-600 mb-1">Answers</div>
                            <div className="text-xs text-gray-500">
                              Avg: {qualityMetrics.content_metrics.answer_length_stats.avg} chars
                              (Min: {qualityMetrics.content_metrics.answer_length_stats.min}, 
                              Max: {qualityMetrics.content_metrics.answer_length_stats.max})
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="bg-white border rounded-lg p-4">
                        <h4 className="font-medium text-gray-900 mb-3">Content Enhancement</h4>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">With Keywords</span>
                            <span className="text-sm font-medium">
                              {qualityMetrics.content_metrics.questions_with_keywords} records
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-600">With Explanations</span>
                            <span className="text-sm font-medium">
                              {qualityMetrics.content_metrics.answers_with_explanations} records
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Quality Issues
                    // {qualityMetrics.quality_score.issues.length > 0 && (
                    //   <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    //     <h4 className="font-medium text-yellow-900 mb-3">Quality Issues & Recommendations</h4>
                    //     <div className="space-y-3">
                    //       {qualityMetrics.quality_score.issues.map((issue, index) => (
                    //         <div key={index} className="flex items-start gap-3">
                    //           <div className={`w-2 h-2 rounded-full mt-2 ${
                    //             issue.severity === 'high' ? 'bg-red-500' :
                    //             issue.severity === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'
                    //           }`}></div>
                    //           <div className="flex-1">
                    //             <div className="text-sm font-medium text-yellow-900">
                    //               {issue.description}
                    //             </div>
                    //             <div className="text-xs text-yellow-700 mt-1">
                    //               {qualityMetrics.quality_comments.records_needing_attention
                    //                 .find(r => r.issue_type === issue.type)?.recommendation}
                    //             </div>
                    //           </div>
                    //         </div>
                    //       ))}
                    //     </div>
                    //   </div>
                    // )} */}

                    {/* Schema Coverage */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <h4 className="font-medium text-blue-900">Schema Coverage</h4>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Info className="h-4 w-4 text-blue-400 hover:text-blue-600 cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            <p className="text-sm">
                              <strong>Schema Coverage:</strong> Measures how many of your defined schema fields are actually being used in the generated data.
                              <br /><br />
                              <strong>Calculation:</strong> (Fields with data / Total schema fields) × 100
                              <br /><br />
                              <strong>Example:</strong> If your schema has 10 fields but only 8 are populated with data, you have 80% schema coverage.
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-blue-900">
                            {qualityMetrics.schema_coverage.fields_utilized}/{qualityMetrics.schema_coverage.total_schema_fields}
                          </div>
                          <div className="text-sm text-blue-600">Fields Utilized</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-blue-900">
                            {qualityMetrics.schema_coverage.coverage_percentage}%
                          </div>
                          <div className="text-sm text-blue-600">Coverage Percentage</div>
                        </div>
                      </div>
                      {qualityMetrics.schema_coverage.unused_fields.length > 0 && (
                        <div className="mt-3">
                          <div className="text-sm text-blue-700 mb-2">Unused fields:</div>
                          <div className="text-xs text-blue-600">
                            {qualityMetrics.schema_coverage.unused_fields.join(', ')}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Grounding Analysis */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <h4 className="font-medium text-green-900">Grounding Analysis</h4>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Info className="h-4 w-4 text-green-400 hover:text-green-600 cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            <p className="text-sm">
                              <strong>Grounding Score:</strong> Measures how well the generated answers are grounded in your source documents.
                              <br /><br />
                              <strong>Calculation (0-100):</strong>
                              <br />• Context Utilization (40%): How much source context is used
                              <br />• Answer-Question Ratio (30%): Answers should be longer than questions
                              <br />• Content Quality (30%): Presence of explanations, keywords, and substantial content
                              <br /><br />
                              <strong>Higher scores</strong> indicate answers that are well-supported by your source material.
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-green-900">
                            {qualityMetrics.grounding_metrics.avg_grounding_score}%
                          </div>
                          <div className="text-sm text-green-600">Average Grounding</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-green-900">
                            {qualityMetrics.grounding_metrics.well_grounded_pairs}
                          </div>
                          <div className="text-sm text-green-600">Well-Grounded Pairs</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-semibold text-green-900">
                            {qualityMetrics.grounding_metrics.grounding_distribution.high}
                          </div>
                          <div className="text-sm text-green-600">High Quality</div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Dataset Generation Dialog */}
          <Dialog open={datasetDialogOpen} onOpenChange={setDatasetDialogOpen}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Generate Full Q&A Dataset</DialogTitle>
                <DialogDescription>
                  Choose how many Q&A pairs to generate
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4">
                {/* Tier Information */}
                <div className="bg-blue-50 p-3 rounded-lg">
                <div className="text-sm text-blue-800">
          <div className="font-medium">📊 You are on <span className="font-semibold">{userProfile?.subscription_tier || 'free'}</span> tier</div>
          <div>Maximum records allowed: <span className="font-semibold">
            {userProfile?.subscription_tier === 'enterprise' ? '5,000' : 
             userProfile?.subscription_tier === 'paid' ? '500' : '50'}
          </span></div>
          {userProfile?.records_generated_this_month && (
            <div className="mt-1">
              <span className="font-medium">Records used this month:</span> <span className="font-semibold">
                {userProfile.records_generated_this_month}
              </span>
            </div>
          )}
          {userProfile?.records_generated_this_month && (
            <div className="mt-1">
              <span className="font-medium">Records remaining:</span> <span className="font-semibold text-green-600">
                {userProfile?.subscription_tier === 'enterprise' ? 5000 : 
                 userProfile?.subscription_tier === 'paid' ? 500 : 50} - {userProfile.records_generated_this_month}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Document-based Recommendation */}
      <div className="bg-green-50 p-3 rounded-lg">
        <div className="text-sm text-green-800">
          <div className="font-medium"> Content Analysis</div>
          <div>Based on your {selectedDocuments.length} selected document(s)</div>
          {selectedDocuments.length > 0 ? (
            <>
              <div className="mt-1">
                <span className="font-medium">Total Pages:</span> {
                  (() => {
                    const selectedDocs = documents.filter(doc => selectedDocuments.includes(doc.id));
                    const totalPages = getTotalPages(selectedDocs);
                    return totalPages > 0 
                      ? `${totalPages} pages`
                      : 'Unknown (processing...)';
                  })()
                }
              </div>
              <div className="mt-1">
                <span className="font-medium">Recommended:</span> <span className="font-semibold">
                  {(() => {
                    const selectedDocs = documents.filter(doc => selectedDocuments.includes(doc.id));
                    const totalPages = getTotalPages(selectedDocs);
                    if (totalPages > 0) {
                      return Math.max(totalPages * 3, selectedDocuments.length * 5);
                    } else {
                      // Fallback: estimate based on document count
                      return selectedDocuments.length * 10;
                    }
                  })()} records
                </span>
              </div>
              <div className="text-xs text-green-600 mt-1">
                {(() => {
                  const selectedDocs = documents.filter(doc => selectedDocuments.includes(doc.id));
                  const totalPages = getTotalPages(selectedDocs);
                  if (totalPages > 0) {
                    return `(Based on ${totalPages} total pages × 3 records per page, minimum ${selectedDocuments.length * 5} records for ${selectedDocuments.length} document(s))`;
                  } else {
                    return `(Page count not available yet. Estimating ${selectedDocuments.length * 10} records based on ${selectedDocuments.length} document(s). This will update once processing is complete.)`;
                  }
                })()}
              </div>
            </>
          ) : (
            <div className="mt-1 text-gray-600">
              No documents selected yet. Go back to select documents for schema generation.
            </div>
          )}
        </div>
      </div>

      {/* Quick Presets */}
      <div>
        <div className="text-sm font-medium text-gray-700 mb-2">Quick Presets</div>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCustomNumRecords(25)}
            className={customNumRecords === 25 ? "border-blue-500 bg-blue-50" : ""}
          >
            25 records
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCustomNumRecords(50)}
            className={customNumRecords === 50 ? "border-blue-500 bg-blue-50" : ""}
          >
            50 records
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCustomNumRecords(100)}
            className={customNumRecords === 100 ? "border-blue-500 bg-blue-50" : ""}
            disabled={userProfile?.subscription_tier === 'free'}
          >
            100 records
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCustomNumRecords(250)}
            className={customNumRecords === 250 ? "border-blue-500 bg-blue-50" : ""}
            disabled={userProfile?.subscription_tier === 'free'}
          >
            250 records
          </Button>
        </div>
      </div>

      {/* Custom Input */}
      <div>
        <Label htmlFor="custom-records">Custom Number of Records</Label>
        <Input
          id="custom-records"
          type="number"
          min={1}
          max={
            userProfile?.subscription_tier === 'enterprise' ? 5000 : 
            userProfile?.subscription_tier === 'paid' ? 500 : 50
          }
          value={customNumRecords}
          onChange={(e) => setCustomNumRecords(parseInt(e.target.value) || 1)}
          placeholder="Enter number of records"
        />
        <div className="text-xs text-gray-500 mt-1">
          Min: 1, Max: {userProfile?.subscription_tier === 'enterprise' ? '5,000' : 
                         userProfile?.subscription_tier === 'paid' ? '500' : '50'}
        </div>
      </div>

      {/* Validation Warning */}
      {customNumRecords > (userProfile?.subscription_tier === 'enterprise' ? 5000 : 
                           userProfile?.subscription_tier === 'paid' ? 500 : 50) && (
        <div className="bg-red-50 p-3 rounded-lg">
          <div className="text-sm text-red-800">
            ⚠️ This exceeds your tier limit. Please upgrade your subscription or reduce the number of records.
          </div>
        </div>
      )}
    </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setDatasetDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button 
              onClick={() => {
                handleGenerateDataset(customNumRecords);
                setDatasetDialogOpen(false);
              }}
              disabled={
                customNumRecords > (userProfile?.subscription_tier === 'enterprise' ? 5000 : 
                                   userProfile?.subscription_tier === 'paid' ? 500 : 50) ||
                customNumRecords < 1
              }
            >
              Generate {customNumRecords} Q&A Pairs
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showDeleteDocDialog} onOpenChange={setShowDeleteDocDialog}>
        <DialogContent>
          <DialogHeader><DialogTitle>Delete Document</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p>Are you sure you want to delete "{docToDelete?.filename}"? This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setShowDeleteDocDialog(false); setDocToDelete(null); }}>Cancel</Button>
              <Button variant="destructive" onClick={confirmDeleteDocument}>Delete Document</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      </div>
    </div>
  );
};

export default ProjectDetail;
