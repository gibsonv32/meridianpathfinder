/**
 * MERIDIAN Dashboard API Client
 * Handles REST API calls to the MERIDIAN backend
 */

const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

export interface Project {
  name: string;
  path: string;
  created_at?: string;
}

export interface ModeStatus {
  id: string;
  name: string;
  status: string;
  verdict?: string;
  artifactCount: number;
  startedAt?: string;
  completedAt?: string;
}

export interface Artifact {
  artifact_id: string;
  artifact_type: string;
  mode: string;
  created_at: string;
  verified: boolean;
}

export interface Deliverable {
  name: string;
  path: string;
  size: number;
  modified_at: string;
}

export interface ApiError {
  detail: string;
}

class MeridianApiClient {
  private baseUrl: string;
  private projectPath: string | null = null;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  setProjectPath(path: string) {
    this.projectPath = path;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = new URL(endpoint, this.baseUrl);
    
    // Add project_path as query param if set
    if (this.projectPath && !url.searchParams.has('project_path')) {
      url.searchParams.set('project_path', this.projectPath);
    }

    const response = await fetch(url.toString(), {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Health check
  async health(): Promise<{ status: string; service: string }> {
    return this.fetch('/');
  }

  // Projects
  async listProjects(): Promise<{ projects: Project[] }> {
    return this.fetch('/projects');
  }

  async initProject(path: string, name: string, force = false): Promise<{ status: string; project_name: string; path: string }> {
    return this.fetch('/project/init', {
      method: 'POST',
      body: JSON.stringify({ path, name, force }),
    });
  }

  async getStatus(): Promise<{
    project_name: string;
    path: string;
    current_mode?: string;
    modes: Array<{
      mode: string;
      status: string;
      verdict?: string;
      artifacts: string[];
    }>;
  }> {
    return this.fetch(`/project/status?project_path=${encodeURIComponent(this.projectPath || '')}`);
  }

  // Modes
  async listModes(): Promise<{ modes: ModeStatus[] }> {
    return this.fetch('/modes');
  }

  async runMode(mode: string, params: Record<string, any> = {}, headless = false): Promise<{ status: string; mode: string; message: string }> {
    return this.fetch('/mode/run', {
      method: 'POST',
      body: JSON.stringify({ mode, params, headless }),
    });
  }

  // Artifacts
  async listArtifacts(options?: {
    artifact_type?: string;
    mode?: string;
    latest_only?: boolean;
  }): Promise<Artifact[]> {
    const params = new URLSearchParams();
    if (this.projectPath) params.set('project_path', this.projectPath);
    if (options?.artifact_type) params.set('artifact_type', options.artifact_type);
    if (options?.mode) params.set('mode', options.mode);
    if (options?.latest_only) params.set('latest_only', 'true');

    return this.fetch(`/artifacts/list?${params.toString()}`);
  }

  async getArtifact(artifactId: string): Promise<any> {
    return this.fetch(`/artifacts/${artifactId}?project_path=${encodeURIComponent(this.projectPath || '')}`);
  }

  async downloadArtifact(artifactId: string): Promise<Blob> {
    const url = `${this.baseUrl}/artifacts/${artifactId}/download?project_path=${encodeURIComponent(this.projectPath || '')}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Download failed');
    return response.blob();
  }

  // Deliverables
  async listDeliverables(): Promise<{ deliverables: Deliverable[] }> {
    return this.fetch('/deliverables');
  }

  async getDeliverable(filename: string): Promise<{ name: string; content: string }> {
    return this.fetch(`/deliverables/${encodeURIComponent(filename)}`);
  }

  // Demo
  async runDemo(dataPath: string, targetCol: string, predictionRow: Record<string, number>): Promise<{
    status: string;
    train: any;
    prediction: any;
  }> {
    const params = new URLSearchParams({
      project_path: this.projectPath || '',
      data_path: dataPath,
      target_col: targetCol,
    });

    return this.fetch(`/demo?${params.toString()}`, {
      method: 'POST',
      body: JSON.stringify(predictionRow),
    });
  }
}

// Export singleton instance
export const api = new MeridianApiClient();

// Export class for custom instances
export { MeridianApiClient };
