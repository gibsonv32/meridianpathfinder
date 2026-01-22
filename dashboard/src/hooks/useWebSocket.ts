import { useEffect, useRef, useCallback } from 'react';
import { useDashboardStore } from '../store';
import type { WSEvent, ModeId, ToolExecution, ArtifactSummary } from '../types';

const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

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
      case 'mode_update': {
        const payload = event.payload as {
          modeId: ModeId;
          status: string;
          verdict?: string;
          message?: string;
        };

        // Update mode state
        updateMode(payload.modeId, {
          status: payload.status as any,
          verdict: payload.verdict as any,
          lastRunAt: event.timestamp,
        });

        // Add activity
        const activityType =
          payload.status === 'running' ? 'mode_running' :
          payload.status === 'completed' ? 'mode_completed' :
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
    }
  }, [addActivity, updateActivity, updateMode, addArtifact]);

  // Send message
  const send = useCallback((type: string, payload: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }));
    } else {
      console.warn('[WS] Cannot send - not connected');
    }
  }, []);

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

  return { send };
}
