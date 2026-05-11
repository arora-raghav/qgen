import React, { useState, useCallback, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Upload, 
  File, 
  X, 
  CheckCircle, 
  AlertCircle, 
  FileText, 
  Image,
  Loader2 
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { documentApi, type UploadResponse } from '@/lib/api';

// Export the interface so parent component can use it
export interface FileWithPreview {
  file: File;  // Store the actual File object
  id: string;
  name: string;
  size: number;
  type: string;
  lastModified: number;
  preview?: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

interface FileUploadProps {
  projectId: string;
  files: FileWithPreview[];           // Accept files from parent
  setFiles: React.Dispatch<React.SetStateAction<FileWithPreview[]>>; // Accept setter from parent
  onUploadComplete?: (response: UploadResponse) => void;
  maxFiles?: number;
  maxFileSize?: number; // in MB
  allowedTypes?: string[];
}

const FileUpload: React.FC<FileUploadProps> = ({
  projectId,
  files,
  setFiles,
  onUploadComplete,
  maxFiles = 5,
  maxFileSize = 5, // MB
  allowedTypes = ['.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg']
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // Generate unique ID for files
  const generateFileId = () => `file_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;

  // File type icon mapping
  const getFileIcon = (type: string | undefined) => {
    if (type && type.startsWith('image/')) return Image;
    return FileText;
  };

  // File validation
  const validateFile = (file: File): string | null => {
    // Check file size
    if (file.size > maxFileSize * 1024 * 1024) {
      return `File size exceeds ${maxFileSize}MB limit`;
    }

    // Check file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedTypes.includes(fileExtension)) {
      return `File type not supported. Allowed: ${allowedTypes.join(', ')}`;
    }

    return null;
  };

  // Handle file selection
  const handleFileSelect = useCallback((selectedFiles: FileList | File[]) => {
    const fileArray = Array.from(selectedFiles);
    
    // Check total file count
    if (files.length + fileArray.length > maxFiles) {
      toast({
        title: "Too many files",
        description: `Maximum ${maxFiles} files allowed`,
        variant: "destructive"
      });
      return;
    }

    const newFiles: FileWithPreview[] = [];

    fileArray.forEach(file => {
      const error = validateFile(file);
      const fileWithPreview: FileWithPreview = {
        file: file,  // Store the actual File object
        id: generateFileId(),
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified,
        status: error ? 'error' : 'pending',
        progress: 0,
        error: error || undefined
      };

      newFiles.push(fileWithPreview);
    });

    setFiles(prev => [...prev, ...newFiles]);
  }, [files.length, maxFiles, maxFileSize, allowedTypes, toast, setFiles]);

  // Handle drag events
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      handleFileSelect(droppedFiles);
    }
  }, [handleFileSelect]);

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files);
    }
  };

  // Remove file
  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  // Upload files
  const handleUpload = async () => {
    const validFiles = files.filter(f => f.status === 'pending');
    
    if (validFiles.length === 0) {
      toast({
        title: "No files to upload",
        description: "Please add valid files before uploading",
        variant: "destructive"
      });
      return;
    }

    setIsUploading(true);

    try {
      // Set all valid files to uploading
      setFiles(prev => prev.map(f => 
        f.status === 'pending' ? { ...f, status: 'uploading' as const, progress: 0 } : f
      ));

      // Simulate progress (since fetch doesn't provide upload progress easily)
      const progressInterval = setInterval(() => {
        setFiles(prev => prev.map(f => 
          f.status === 'uploading' ? { 
            ...f, 
            progress: Math.min(f.progress + Math.random() * 30, 90) 
          } : f
        ));
      }, 500);

      // Extract the actual File objects
      const filesToUpload = validFiles.map(f => f.file);

      const response = await documentApi.uploadDocuments(projectId, filesToUpload);

      clearInterval(progressInterval);

      // Update file statuses based on response
      setFiles(prev => prev.map(f => {
        if (f.status === 'uploading') {
          const uploaded = response.uploaded_files.find(uf => uf.filename === f.name);
          const error = response.errors.find(err => err.includes(f.name));
          
          return {
            ...f,
            status: uploaded ? 'success' as const : 'error' as const,
            progress: 100,
            error: error || undefined
          };
        }
        return f;
      }));

      // Show success message
      toast({
        title: "Upload Complete",
        description: `${response.total_uploaded} files uploaded successfully`,
      });

      // Call completion callback
      onUploadComplete?.(response);

    } catch (error: any) {
      console.error('Upload error:', error);
      
      // Set all uploading files to error
      setFiles(prev => prev.map(f => 
        f.status === 'uploading' ? { 
          ...f, 
          status: 'error' as const, 
          progress: 0, 
          error: error.message || 'Upload failed' 
        } : f
      ));

      toast({
        title: "Upload Failed",
        description: error.message || "Failed to upload files",
        variant: "destructive"
      });
    } finally {
      setIsUploading(false);
    }
  };

  // Clear all files
  const clearFiles = () => {
    setFiles([]);
  };

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <Card 
        className={`relative border-2 border-dashed transition-colors duration-200 ${
          isDragOver 
            ? 'border-blue-500 bg-blue-50' 
            : files.length > 0 
              ? 'border-green-300 bg-green-50' 
              : 'border-gray-300 bg-gray-50 hover:border-gray-400'
        }`}
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <CardContent className="flex flex-col items-center justify-center py-12 px-6 text-center">
          <div className={`mb-4 p-3 rounded-full ${
            files.length > 0 ? 'bg-green-100' : 'bg-gray-100'
          }`}>
            <Upload className={`h-8 w-8 ${
              files.length > 0 ? 'text-green-600' : 'text-gray-400'
            }`} />
          </div>
          
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {files.length > 0 ? `${files.length} file(s) selected` : 'Upload Documents'}
          </h3>
          
          <p className="text-sm text-gray-600 mb-4">
            Drag and drop files here, or click to browse
          </p>
          
          <p className="text-xs text-gray-500 mb-6">
            Supports: {allowedTypes.join(', ')} • Max {maxFileSize}MB per file • Up to {maxFiles} files
          </p>
          
          <Button 
            onClick={() => fileInputRef.current?.click()}
            variant="outline"
            disabled={isUploading}
          >
            <Upload className="h-4 w-4 mr-2" />
            Choose Files
          </Button>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={allowedTypes.join(',')}
            onChange={handleFileInputChange}
            className="hidden"
          />
        </CardContent>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <div className="flex justify-between items-center mb-4">
              <h4 className="font-semibold text-gray-900">Selected Files</h4>
              <div className="space-x-2">
                <Button 
                  onClick={clearFiles} 
                  variant="outline" 
                  size="sm"
                  disabled={isUploading}
                >
                  Clear All
                </Button>
                <Button 
                  onClick={handleUpload}
                  disabled={isUploading || files.filter(f => f.status === 'pending').length === 0}
                  size="sm"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4 mr-2" />
                      Upload Files
                    </>
                  )}
                </Button>
              </div>
            </div>
            
            <div className="space-y-3">
              {files.map((file) => {
                const IconComponent = getFileIcon(file.type);
                
                return (
                  <div key={file.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0">
                      <IconComponent className="h-8 w-8 text-gray-400" />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </p>
                        <div className="flex items-center space-x-2">
                          {file.status === 'success' && (
                            <CheckCircle className="h-5 w-5 text-green-500" />
                          )}
                          {file.status === 'error' && (
                            <AlertCircle className="h-5 w-5 text-red-500" />
                          )}
                          {file.status === 'uploading' && (
                            <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                          )}
                          <Button
                            onClick={() => removeFile(file.id)}
                            variant="ghost"
                            size="sm"
                            disabled={isUploading}
                            className="h-6 w-6 p-0"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between mt-1">
                        <p className="text-xs text-gray-500">
                          {file.size ? (file.size / (1024 * 1024)).toFixed(1) : '0'} MB
                        </p>
                        {file.status === 'error' && file.error && (
                          <p className="text-xs text-red-500">{file.error}</p>
                        )}
                      </div>
                      
                      {(file.status === 'uploading' || file.status === 'success') && (
                        <Progress value={file.progress} className="mt-2 h-1" />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default FileUpload;
