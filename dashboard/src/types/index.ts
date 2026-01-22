// =============================================================================
// MERIDIAN Dashboard Type Definitions
// =============================================================================

// -----------------------------------------------------------------------------
// Mode & Pipeline Types
// -----------------------------------------------------------------------------
export type ModeId = '0' | '0.5' | '1' | '2' | '3' | '4' | '5' | '6' | '6.5' | '7';

export type ModeStatus = 'not_started' | 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export type GateVerdict = 'go' | 'conditional' | 'no_go' | 'blocked';

export interface ModeInfo {
  id: ModeId;
  name: string;
  description: string;
  status: ModeStatus;
  verdict?: GateVerdict;
  lastRunAt?: string;
  lastRunId?: string;
  artifactCount: number;
}

export const MODE_DEFINITIONS: Record<ModeId, { name: string; description: string }> = {
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

// -----------------------------------------------------------------------------
// Activity Feed Types
// -----------------------------------------------------------------------------
export type ActivityType = 
  | 'mode_started'
  | 'mode_running'
  | 'mode_completed'
  | 'mode_failed'
  | 'tool_execution'
  | 'artifact_created'
  | 'system_notice'
  | 'user_command'
  | 'llm_response';

export type ToolStatus = 'running' | 'success' | 'error';

export interface ToolExecution {
  id: string;
  type: 'bash' | 'python' | 'api' | 'llm';
  command?: string;
  summary: string;
  status: ToolStatus;
  output?: string;
  exitCode?: number;
  runtime?: number;
  artifactId?: string;
  startedAt: string;
  completedAt?: string;
}

export interface ActivityItem {
  id: string;
  type: ActivityType;
  timestamp: string;
  modeId?: ModeId;
  content?: string;
  tool?: ToolExecution;
  artifact?: ArtifactSummary;
  severity?: 'info' | 'warning' | 'error';
  isPinned?: boolean;
  annotation?: string;
}

// -----------------------------------------------------------------------------
// Artifact Types
// -----------------------------------------------------------------------------
export type ArtifactType = 
  | 'Mode0GatePacket'
  | 'OpportunityBrief'
  | 'OpportunityBacklog'
  | 'DecisionIntelProfile'
  | 'FeasibilityReport'
  | 'ModelRecommendations'
  | 'FeatureRegistry'
  | 'BusinessCaseScorecard'
  | 'ThresholdFramework'
  | 'CodeGenerationPlan'
  | 'ExecutionOpsScorecard'
  | 'InterpretationPackage'
  | 'DeliveryManifest'
  | 'DataFile'
  | 'Unknown';

export interface ArtifactSummary {
  id: string;
  type: ArtifactType;
  modeId: ModeId;
  name: string;
  createdAt: string;
  verified?: boolean;
}

export interface Artifact extends ArtifactSummary {
  path: string;
  size: number;
  checksum?: string;
  metadata?: Record<string, unknown>;
  parentArtifacts?: string[];
  content?: unknown;
}

// -----------------------------------------------------------------------------
// Attachment Types
// -----------------------------------------------------------------------------
export type AttachmentStatus = 'pending' | 'uploading' | 'success' | 'error';

export interface Attachment {
  id: string;
  file: File;
  name: string;
  type: string;
  size: number;
  status: AttachmentStatus;
  progress: number;
  error?: string;
  artifactId?: string;
}

// -----------------------------------------------------------------------------
// Project Types
// -----------------------------------------------------------------------------
export type ConnectionStatus = 'connected' | 'connecting' | 'reconnecting' | 'offline';

export interface Project {
  id: string;
  name: string;
  path: string;
  createdAt: string;
  currentMode?: ModeId;
}

// -----------------------------------------------------------------------------
// WebSocket Event Types
// -----------------------------------------------------------------------------
export type WSEventType = 
  | 'mode_update'
  | 'tool_output'
  | 'artifact_created'
  | 'connection_status'
  | 'error';

export interface WSEvent {
  type: WSEventType;
  payload: unknown;
  timestamp: string;
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

export interface RunModeParams {
  modeId: ModeId;
  params?: Record<string, unknown>;
  headless?: boolean;
  dataFile?: string;
  target?: string;
}
