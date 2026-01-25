import { useEffect, useRef, useCallback } from 'react';
import { useDashboardStore } from '../store';
import type { WSEvent, ModeId, ToolExecution, ArtifactSummary, ModeInfo } from '../types';

const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

// Get project path from env or default
const getProjectPath = () => {
  return (import.meta as any).env?.VITE_PROJECT_PATH || '/home/gibsonv32/dev/meridian';
};

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const {
    setConnectionStatus,
    addActivity,
    updateActivity,
    updateMode,
    addArtifact,
    setArtifacts,
  } = useDashboardStore();

  const connect = useCallback(() => {
    // Don't reconnect if already connected or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setConnectionStatus('connecting');
    console.log('[WS] Connecting to', WS_URL);

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected');
      setConnectionStatus('connected');
      reconnectAttemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const wsEvent: WSEvent = JSON.parse(event.data);
        handleEvent(wsEvent);
      } catch (error) {
        console.error('[WS] Failed to parse message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
    };

    ws.onclose = (event) => {
      console.log('[WS] Disconnected:', event.code, event.reason);
      wsRef.current = null;

      // Attempt reconnect
      if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        setConnectionStatus('reconnecting');
        reconnectAttemptRef.current++;
        
        const delay = RECONNECT_DELAY * Math.min(reconnectAttemptRef.current, 5);
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})`);
        
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      } else {
        setConnectionStatus('offline');
      }
    };
  }, [setConnectionStatus]);

  const handleEvent = useCallback((event: WSEvent) => {
    console.log('[WS] Event:', event.type, event.payload);

    switch (event.type) {
      case 'connected': {
        // Server confirmed connection - handled silently
        // Connection status is shown in the header, no need for activity log
        const payload = event.payload as { message: string };
        console.log('[WS] Connected:', payload.message);
        break;
      }

      case 'mode_update': {
        const payload = event.payload as {
          modeId: ModeId;
          status: string;
          verdict?: string;
          message?: string;
        };

        // Update mode state
        updateMode(payload.modeId, {
          status: (payload.status === 'complete' ? 'completed' : payload.status) as ModeInfo['status'],
          verdict: payload.verdict as ModeInfo['verdict'],
          lastRunAt: event.timestamp,
        });

        // Add activity
        const activityType =
          payload.status === 'running' ? 'mode_running' :
          payload.status === 'completed' || payload.status === 'complete' ? 'mode_completed' :
          payload.status === 'failed' ? 'mode_failed' : 'mode_started';

        addActivity({
          id: crypto.randomUUID(),
          type: activityType,
          timestamp: event.timestamp,
          modeId: payload.modeId,
          content: payload.message,
        });
        break;
      }

      case 'status_response': {
        // Response to /status command
        const payload = event.payload as {
          project_name: string;
          modes: Array<{ id: string; status: string; verdict?: string; artifactCount: number }>;
        };
        
        // Update all modes
        payload.modes.forEach(m => {
          updateMode(m.id as ModeId, {
            status: (m.status === 'complete' ? 'completed' : m.status) as ModeInfo['status'],
            verdict: m.verdict as ModeInfo['verdict'],
            artifactCount: m.artifactCount,
          });
        });
        break;
      }

      case 'artifacts_response': {
        // Response to /artifacts command
        const payload = event.payload as {
          artifacts: Array<{
            id: string;
            type: string;
            modeId: string;
            createdAt: string;
            name: string;
          }>;
        };
        
        const artifacts: ArtifactSummary[] = payload.artifacts.map(a => ({
          id: a.id,
          type: a.type,
          modeId: a.modeId as ModeId,
          createdAt: a.createdAt,
          name: a.name,
        }));
        
        setArtifacts(artifacts);
        break;
      }

      case 'tool_output': {
        const payload = event.payload as {
          activityId?: string;
          tool: ToolExecution;
        };

        if (payload.activityId) {
          // Update existing activity
          updateActivity(payload.activityId, { tool: payload.tool });
        } else {
          // Add new activity
          addActivity({
            id: payload.tool.id || crypto.randomUUID(),
            type: 'tool_execution',
            timestamp: event.timestamp,
            tool: payload.tool,
          });
        }
        break;
      }

      case 'artifact_created': {
        const artifact = event.payload as ArtifactSummary;
        
        addArtifact(artifact);
        addActivity({
          id: crypto.randomUUID(),
          type: 'artifact_created',
          timestamp: event.timestamp,
          modeId: artifact.modeId,
          artifact,
        });

        // Update mode artifact count
        const store = useDashboardStore.getState();
        const mode = store.modes.find(m => m.id === artifact.modeId);
        if (mode) {
          updateMode(artifact.modeId, {
            artifactCount: mode.artifactCount + 1,
          });
        }
        break;
      }

      case 'error': {
        const payload = event.payload as { message: string; severity?: string };
        addActivity({
          id: crypto.randomUUID(),
          type: 'system_notice',
          timestamp: event.timestamp,
          content: payload.message,
          severity: (payload.severity as any) || 'error',
        });
        break;
      }

      case 'pong': {
        // Heartbeat response - no action needed
        break;
      }
    }
  }, [addActivity, updateActivity, updateMode, addArtifact, setArtifacts]);

  // Send message
  const send = useCallback((type: string, payload: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }));
      return true;
    } else {
      console.warn('[WS] Cannot send - not connected');
      return false;
    }
  }, []);

  // Send a command (slash command)
  const sendCommand = useCallback((command: string, args: Record<string, unknown> = {}) => {
    return send('command', {
      command,
      args: {
        ...args,
        project_path: getProjectPath(),
      },
    });
  }, [send]);

  // Run a mode
  const runMode = useCallback((modeId: string, params: Record<string, unknown> = {}) => {
    return send('run_mode', {
      project_path: getProjectPath(),
      mode: modeId,
      params,
    });
  }, [send]);

  // Subscribe to project updates
  const subscribe = useCallback((projectPath: string) => {
    return send('subscribe', { project_path: projectPath });
  }, [send]);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  // Keyboard shortcut for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        useDashboardStore.getState().setSearchOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return { send, sendCommand, runMode, subscribe };
}
