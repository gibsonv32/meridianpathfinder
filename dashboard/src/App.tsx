import { useEffect, useCallback } from 'react';
import { Toaster } from 'react-hot-toast';
import toast from 'react-hot-toast';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { MeridianDesktop } from './components/MeridianDesktop';
import { MeridianV2 } from './components/MeridianV2';
import { MeridianV3 } from './components/MeridianV3';
import { MeridianV4 } from './components/MeridianV4';
import { MeridianPro } from './components/MeridianPro';
import { useDashboardStore } from './store';
import { useWebSocket } from './hooks/useWebSocket';
import { api } from './api/client';
import type { ModeInfo, ModeId, ArtifactSummary } from './types';

export function App() {
  const {
    setConnectionStatus,
    setCurrentProject,
    setModes,
    setArtifacts,
    addActivity,
  } = useDashboardStore();
  
  // Initialize WebSocket connection
  useWebSocket();

  // Load initial data from API
  const loadProjectData = useCallback(async () => {
    try {
      // Get project path from env or use DGX default
      const projectPath = import.meta.env.VITE_PROJECT_PATH || "/home/gibsonv32/dev/meridian";
      
      api.setProjectPath(projectPath);
      
      // Check API health first
      const health = await api.health();
      if (health.status !== 'ok') {
        throw new Error('API not healthy');
      }
      
      setConnectionStatus('connected');
      
      // Load project status
      const status = await api.getStatus();
      setCurrentProject({
        id: status.project_name.toLowerCase().replace(/\s+/g, '-'),
        name: status.project_name,
        path: status.path,
        createdAt: new Date().toISOString(),
      });
      
      // Convert modes to dashboard format
      const modeDefinitions: Record<string, { name: string; description: string }> = {
        '0': { name: 'EDA', description: 'Exploratory Data Analysis' },
        '0.5': { name: 'Opportunity', description: 'Opportunity Discovery' },
        '1': { name: 'Decision Intel', description: 'Decision Intelligence Profile' },
        '2': { name: 'Feasibility', description: 'Feasibility Assessment' },
        '3': { name: 'Strategy', description: 'Model Strategy & Features' },
        '4': { name: 'Business Case', description: 'Business Case Scorecard' },
        '5': { name: 'Code Gen', description: 'Code Generation Plan' },
        '6': { name: 'Execution', description: 'Execution & Operations' },
        '6.5': { name: 'Interpretation', description: 'Model Interpretation' },
        '7': { name: 'Delivery', description: 'Delivery Manifest' },
      };
      
      const modes: ModeInfo[] = status.modes.map(m => ({
        id: m.mode as ModeId,
        name: modeDefinitions[m.mode]?.name || `Mode ${m.mode}`,
        description: modeDefinitions[m.mode]?.description || '',
        status: (m.status === 'complete' ? 'completed' : m.status) as ModeInfo['status'],
        verdict: m.verdict as ModeInfo['verdict'],
        artifactCount: m.artifacts?.length || 0,
      }));
      
      setModes(modes);
      
      // Load artifacts
      const artifactList = await api.listArtifacts({ latest_only: true });
      const artifacts: ArtifactSummary[] = artifactList.map(a => ({
        id: a.artifact_id,
        type: a.artifact_type,
        modeId: a.mode as ModeId,
        createdAt: a.created_at,
        name: a.artifact_type,
        verified: a.verified,
      }));
      
      setArtifacts(artifacts);
      
      // Connection status is shown in header - no toast needed
      
    } catch (error) {
      console.error('Failed to load project data:', error);
      setConnectionStatus('offline');
      
      // Show error in toast only - connection status is shown in header
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast.error(`Backend unavailable: ${errorMessage}`);
    }
  }, [setConnectionStatus, setCurrentProject, setModes, setArtifacts, addActivity]);

  // Load data on mount
  useEffect(() => {
    loadProjectData();
  }, [loadProjectData]);

  return (
    <BrowserRouter>
      <div className="relative">
        
        <Routes>
          <Route path="/classic" element={<Layout />} />
          <Route path="/desktop" element={<MeridianDesktop />} />
          <Route path="/v2" element={<MeridianV2 />} />
          <Route path="/v3" element={<MeridianV3 />} />
          <Route path="/v4" element={<MeridianV4 />} />
          <Route path="/pro" element={<MeridianPro />} />
          <Route path="/" element={<Navigate to="/desktop" replace />} />
        </Routes>
        
        <Toaster
          position="bottom-right"
          toastOptions={{
            className: 'toast-container',
            style: {
              background: '#1f1f1f',
              color: '#f5f5f5',
              border: '1px solid #333333',
              borderRadius: '8px',
              fontSize: '14px',
            },
            success: {
              iconTheme: {
                primary: '#22c55e',
                secondary: '#1f1f1f',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#1f1f1f',
              },
            },
          }}
        />
      </div>
    </BrowserRouter>
  );
}
