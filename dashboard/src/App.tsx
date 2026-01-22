import { useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { Layout } from './components/Layout';
import { useDashboardStore } from './store';
import { useWebSocket } from './hooks/useWebSocket';

export function App() {
  const setConnectionStatus = useDashboardStore((s) => s.setConnectionStatus);
  
  // Initialize WebSocket connection
  useWebSocket();

  // Simulate initial connection
  useEffect(() => {
    const timer = setTimeout(() => {
      setConnectionStatus('connected');
    }, 1000);
    return () => clearTimeout(timer);
  }, [setConnectionStatus]);

  return (
    <>
      <Layout />
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
    </>
  );
}
