import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Trash2, FileText, Upload, Database, ArrowRight, Zap, Calendar } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { documentApi, type Project } from '@/lib/api';

// Document Workspace Component
const DocumentWorkspace: React.FC<{ user: any }> = ({ user }) => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [newProjectInstruction, setNewProjectInstruction] = useState('');
  const [userProfile, setUserProfile] = useState<any>(null);
  const [showDeleteProjectDialog, setShowDeleteProjectDialog] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const { toast } = useToast();

  const loadUserProfile = useCallback(async () => {
    try {
      const profile = await documentApi.getUserProfile();
      setUserProfile(profile);
    } catch (error) {
      console.error('Error loading user profile:', error);
    }
  }, []);

  const loadProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const projectsData = await documentApi.getProjects();
      setProjects(projectsData);
    } catch (error) {
      console.error('Error loading projects:', error);
      toast({ title: "Error", description: "Failed to load projects. Please try again.", variant: "destructive" });
    } finally {
      setLoadingProjects(false);
    }
  }, [toast]);

  useEffect(() => {
    if (user) {
      Promise.all([loadProjects(), loadUserProfile()]).catch(() => {});
    }
  }, [user, loadProjects, loadUserProfile]);

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      toast({ title: "Error", description: "Project name is required", variant: "destructive" });
      return;
    }
    const tempProject: Project = {
      id: `temp-${Date.now()}`, name: newProjectName.trim(), description: newProjectDescription.trim() || '',
      instruction: newProjectInstruction.trim() || '', status: 'creating',
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(), user_id: 'local'
    };
    setProjects(prev => [tempProject, ...prev]);
    try {
      const newProject = await documentApi.createProject({
        name: newProjectName.trim(),
        description: newProjectDescription.trim() || undefined,
        instruction: newProjectInstruction.trim() || undefined,
      });
      setProjects(prev => prev.map(p => p.id === tempProject.id ? newProject : p));
      toast({ title: "Success", description: "Project created successfully" });
      setNewProjectName(''); setNewProjectDescription(''); setNewProjectInstruction('');
      setShowCreateProject(false);
    } catch (error: any) {
      setProjects(prev => prev.filter(p => p.id !== tempProject.id));
      toast({ title: "Error", description: error.message || "Failed to create project", variant: "destructive" });
    }
  };

  const handleViewProject = (project: Project) => {
    navigate(`/project/${project.id}`);
  };

  const handleDeleteProject = (project: Project) => {
    setProjectToDelete(project); setShowDeleteProjectDialog(true);
  };

  const confirmDeleteProject = async () => {
    if (!projectToDelete) return;
    const previousProjects = projects;
    setProjects(prev => prev.filter(p => p.id !== projectToDelete.id));
    try {
      await documentApi.deleteProject(projectToDelete.id);
      toast({ title: "Success", description: "Project deleted successfully" });
    } catch (error: any) {
      setProjects(previousProjects);
      toast({ title: "Error", description: error.message || "Failed to delete project", variant: "destructive" });
    } finally {
      setShowDeleteProjectDialog(false); setProjectToDelete(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-blue-100 rounded-xl"><Database className="h-6 w-6 text-blue-600" /></div>
              <div><p className="text-sm font-medium text-gray-600">Active Projects</p><p className="text-2xl font-bold text-gray-900">{projects.length}</p></div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-green-100 rounded-xl"><FileText className="h-6 w-6 text-green-600" /></div>
              <div><p className="text-sm font-medium text-gray-600">Documents Processed</p><p className="text-2xl font-bold text-gray-900">{userProfile?.total_documents || 0}</p></div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-purple-100 rounded-xl"><Upload className="h-6 w-6 text-purple-600" /></div>
              <div><p className="text-sm font-medium text-gray-600">Storage Used</p><p className="text-2xl font-bold text-gray-900">{userProfile?.storage_used_mb?.toFixed(1) || '0'} MB</p></div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="flex items-center gap-2"><Database className="h-5 w-5" />Document Processing Projects</CardTitle>
              <p className="text-sm text-gray-600 mt-1">Transform your documents into AI training datasets</p>
            </div>
            <Button onClick={() => setShowCreateProject(true)} className="bg-blue-600 hover:bg-blue-700">
              <Upload className="h-4 w-4 mr-2" />New Project
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadingProjects ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading projects...</p>
            </div>
          ) : projects.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <Database className="h-8 w-8 text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Ready to get started?</h3>
              <p className="text-gray-600 mb-8 max-w-md mx-auto">Create your first project and start transforming documents into high-quality training data.</p>
              <Button onClick={() => setShowCreateProject(true)} className="bg-blue-600 hover:bg-blue-700">
                <Upload className="h-4 w-4 mr-2" />Create Your First Project
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {projects.map((project) => (
                <Card key={project.id} className="border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all duration-200">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-lg text-gray-900">{project.name}</h3>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${project.status === 'completed' ? 'bg-green-100 text-green-700' : project.status === 'processing' ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'}`}>
                            {project.status}
                          </div>
                        </div>
                        {project.description && <p className="text-gray-600 text-sm mb-3">{project.description}</p>}
                        <div className="flex items-center gap-6 text-xs text-gray-500">
                          <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />Created: {new Date(project.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Button variant="outline" size="sm" onClick={() => handleViewProject(project)} className="hover:bg-blue-50 hover:border-blue-300">
                          <ArrowRight className="h-4 w-4 mr-1" />Open Project
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleDeleteProject(project)} className="text-red-600 hover:text-red-700 hover:bg-red-50 hover:border-red-300">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showCreateProject} onOpenChange={setShowCreateProject}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-blue-600" />Create New Project
            </DialogTitle>
            <p className="text-sm text-gray-600 mt-2">Start by creating a project where you can upload documents and generate synthetic training data.</p>
          </DialogHeader>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Project Name *</label>
              <Input value={newProjectName} onChange={(e) => setNewProjectName(e.target.value)} placeholder="e.g., Financial Report Analysis" className="w-full" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Description <span className="text-gray-500 font-normal">(optional)</span></label>
              <Input value={newProjectDescription} onChange={(e) => setNewProjectDescription(e.target.value)} placeholder="Brief description of your project" className="w-full" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Data Extraction Instructions <span className="text-gray-500 font-normal">(optional)</span></label>
              <Input value={newProjectInstruction} onChange={(e) => setNewProjectInstruction(e.target.value)} placeholder="What data should be extracted?" className="w-full" />
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button variant="outline" onClick={() => setShowCreateProject(false)}>Cancel</Button>
              <Button onClick={handleCreateProject} disabled={!newProjectName.trim()} className="bg-blue-600 hover:bg-blue-700">
                <Upload className="h-4 w-4 mr-2" />Create Project
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showDeleteProjectDialog} onOpenChange={setShowDeleteProjectDialog}>
        <DialogContent>
          <DialogHeader><DialogTitle>Delete Project</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p>Are you sure you want to delete "{projectToDelete?.name}"? This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setShowDeleteProjectDialog(false); setProjectToDelete(null); }}>Cancel</Button>
              <Button variant="destructive" onClick={confirmDeleteProject}>Delete Project</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const Dashboard: React.FC = () => {
  // No auth — set a default local user immediately
  const [user] = useState<any>({ id: 'local', email: 'local@qgen.app' });
  const [loading] = useState(false);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50">
        <div className="w-full max-w-md p-8 space-y-6 bg-white rounded shadow">
          <h2 className="text-2xl font-bold text-center">Loading...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900">QGen</h1>
          </div>
        </div>
        <DocumentWorkspace user={user} />
      </div>
    </div>
  );
};

export default Dashboard;
