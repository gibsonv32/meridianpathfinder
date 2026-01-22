// =============================================================================
// MERIDIAN Dashboard Global Store (Zustand)
// =============================================================================

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type {
  Project,
  ModeInfo,
  ModeId,
  ActivityItem,
  Artifact,
  ArtifactSummary,
  Attachment,
  ConnectionStatus,
} from '../types';

// -----------------------------------------------------------------------------
// Store State Types
// -----------------------------------------------------------------------------
interface DashboardState {
  // Connection
  connectionStatus: ConnectionStatus;
  setConnectionStatus: (status: ConnectionStatus) => void;

  // Project
  currentProject: Project | null;
  setCurrentProject: (project: Project | null) => void;

  // Modes
  modes: ModeInfo[];
  setModes: (modes: ModeInfo[]) => void;
  updateMode: (modeId: ModeId, updates: Partial<ModeInfo>) => void;

  // Activity Feed
  activities: ActivityItem[];
  addActivity: (activity: ActivityItem) => void;
  updateActivity: (id: string, updates: Partial<ActivityItem>) => void;
  clearActivities: () => void;
  toggleActivityPin: (id: string) => void;
  setActivityAnnotation: (id: string, annotation: string) => void;

  // Artifacts
  artifacts: ArtifactSummary[];
  setArtifacts: (artifacts: ArtifactSummary[]) => void;
  addArtifact: (artifact: ArtifactSummary) => void;
  selectedArtifact: Artifact | null;
  setSelectedArtifact: (artifact: Artifact | null) => void;

  // Attachments
  attachments: Attachment[];
  addAttachment: (attachment: Attachment) => void;
  updateAttachment: (id: string, updates: Partial<Attachment>) => void;
  removeAttachment: (id: string) => void;
  clearAttachments: () => void;

  // UI State
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  activePanel: 'pipeline' | 'artifacts' | 'pinned';
  setActivePanel: (panel: 'pipeline' | 'artifacts' | 'pinned') => void;
  commandHistory: string[];
  addToCommandHistory: (command: string) => void;

  // Search
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
}

// -----------------------------------------------------------------------------
// Initial Mode State
// -----------------------------------------------------------------------------
const createInitialModes = (): ModeInfo[] => {
  const modeIds: ModeId[] = ['0', '0.5', '1', '2', '3', '4', '5', '6', '6.5', '7'];
  const definitions: Record<ModeId, { name: string; description: string }> = {
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
  
  return modeIds.map(id => ({
    id,
    name: definitions[id].name,
    description: definitions[id].description,
    status: 'not_started' as const,
    artifactCount: 0,
  }));
};

// -----------------------------------------------------------------------------
// Store Implementation
// -----------------------------------------------------------------------------
export const useDashboardStore = create<DashboardState>()(
  subscribeWithSelector((set) => ({
    // Connection
    connectionStatus: 'connecting',
    setConnectionStatus: (status) => set({ connectionStatus: status }),

    // Project
    currentProject: null,
    setCurrentProject: (project) => set({ currentProject: project }),

    // Modes
    modes: createInitialModes(),
    setModes: (modes) => set({ modes }),
    updateMode: (modeId, updates) =>
      set((state) => ({
        modes: state.modes.map((m) =>
          m.id === modeId ? { ...m, ...updates } : m
        ),
      })),

    // Activity Feed
    activities: [],
    addActivity: (activity) =>
      set((state) => ({
        activities: [activity, ...state.activities].slice(0, 500), // Keep last 500
      })),
    updateActivity: (id, updates) =>
      set((state) => ({
        activities: state.activities.map((a) =>
          a.id === id ? { ...a, ...updates } : a
        ),
      })),
    clearActivities: () => set({ activities: [] }),
    toggleActivityPin: (id) =>
      set((state) => ({
        activities: state.activities.map((a) =>
          a.id === id ? { ...a, isPinned: !a.isPinned } : a
        ),
      })),
    setActivityAnnotation: (id, annotation) =>
      set((state) => ({
        activities: state.activities.map((a) =>
          a.id === id ? { ...a, annotation } : a
        ),
      })),

    // Artifacts
    artifacts: [],
    setArtifacts: (artifacts) => set({ artifacts }),
    addArtifact: (artifact) =>
      set((state) => ({
        artifacts: [artifact, ...state.artifacts],
      })),
    selectedArtifact: null,
    setSelectedArtifact: (artifact) => set({ selectedArtifact: artifact }),

    // Attachments
    attachments: [],
    addAttachment: (attachment) =>
      set((state) => ({
        attachments: [...state.attachments, attachment],
      })),
    updateAttachment: (id, updates) =>
      set((state) => ({
        attachments: state.attachments.map((a) =>
          a.id === id ? { ...a, ...updates } : a
        ),
      })),
    removeAttachment: (id) =>
      set((state) => ({
        attachments: state.attachments.filter((a) => a.id !== id),
      })),
    clearAttachments: () => set({ attachments: [] }),

    // UI State
    sidebarCollapsed: false,
    toggleSidebar: () =>
      set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
    activePanel: 'pipeline',
    setActivePanel: (panel) => set({ activePanel: panel }),
    commandHistory: [],
    addToCommandHistory: (command) =>
      set((state) => ({
        commandHistory: [command, ...state.commandHistory].slice(0, 100),
      })),

    // Search
    searchQuery: '',
    setSearchQuery: (query) => set({ searchQuery: query }),
    searchOpen: false,
    setSearchOpen: (open) => set({ searchOpen: open }),
  }))
);

// Selectors
export const selectPinnedActivities = (state: DashboardState) =>
  state.activities.filter((a) => a.isPinned);

export const selectActivitiesByMode = (modeId: ModeId) => (state: DashboardState) =>
  state.activities.filter((a) => a.modeId === modeId);

export const selectArtifactsByMode = (modeId: ModeId) => (state: DashboardState) =>
  state.artifacts.filter((a) => a.modeId === modeId);

export const selectRunningMode = (state: DashboardState) =>
  state.modes.find((m) => m.status === 'running');
