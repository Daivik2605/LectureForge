'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { getWebSocketUrl, JobStatus } from '@/lib/api';

interface UseJobWebSocketReturn {
  status: JobStatus | null;
  isConnected: boolean;
  error: string | null;
}

export function useJobWebSocket(jobId: string, retryToken: number = 0): UseJobWebSocketReturn {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(getWebSocketUrl(jobId));

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message:', data.type, data);
          
          if (data.type === 'connected' || data.type === 'status') {
            setStatus((prev) => ({
              ...prev,
              ...data.data,
            } as JobStatus));
          } else if (data.type === 'progress') {
            setStatus((prev) => ({
              ...prev,
              ...data.data,
            } as JobStatus));
          } else if (data.type === 'completed') {
            // Job completed - update status to trigger redirect
            setStatus((prev) => ({
              ...prev,
              status: 'completed',
              progress: 100,
            } as JobStatus));
          } else if (data.type === 'error') {
            setError(data.data?.error || data.message || 'An error occurred');
            setStatus((prev) => ({
              ...prev,
              status: 'failed',
              error: data.data?.error || data.message,
            } as JobStatus));
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('Connection error');
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        wsRef.current = null;

        // Reconnect if not a normal close and job is still processing
        if (event.code !== 1000 && status?.status === 'processing') {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      setError('Failed to connect');
    }
  }, [jobId, status?.status, retryToken]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000);
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { status, isConnected, error };
}
