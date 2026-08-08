/** WebSocket hook for real-time mission events */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { TelemetrySample } from '../types/mission';
import type { WSMessage } from '../api/mission';
import { missionKeys } from './useMission';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

interface UseMissionSocketOptions {
  enabled?: boolean;
  onTelemetryUpdate?: (telemetry: TelemetrySample) => void;
}

interface UseMissionSocketReturn {
  connectionStatus: ConnectionStatus;
  lastMessage: WSMessage | null;
  sendMessage: (message: string) => void;
}

/**
 * Hook to manage WebSocket connection to the mission backend.
 * Derives WS URL from window.location to avoid hardcoding.
 * Handles reconnection with exponential backoff.
 */
export function useMissionSocket(
  options: UseMissionSocketOptions = {}
): UseMissionSocketReturn {
  const { enabled = true, onTelemetryUpdate } = options;
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);

  // Derive WebSocket URL from current page location
  const getWsUrl = useCallback((): string => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/ws/mission`;
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;

    const url = getWsUrl();
    setConnectionStatus('connecting');

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        setLastMessage(message);

        // Handle specific event types
        switch (message.event) {
          case 'telemetry.updated':
            // Direct telemetry update - can update UI immediately without refetch
            if (onTelemetryUpdate && message.payload) {
              onTelemetryUpdate(message.payload as TelemetrySample);
            }
            break;

          case 'mission.started':
          case 'mission.paused':
          case 'mission.resumed':
          case 'anomaly.injected':
          case 'plans.generated':
          case 'plan.approved':
          case 'mission.reset':
            // Invalidate mission state to refetch authoritative data
            queryClient.invalidateQueries({ queryKey: missionKeys.state() });
            break;

          default:
            // Unknown event - still invalidate to be safe
            queryClient.invalidateQueries({ queryKey: missionKeys.state() });
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      if (wsRef.current === ws) {
        wsRef.current = null;
      }

      if (reconnectAttemptsRef.current < maxReconnectAttempts && enabled) {
        setConnectionStatus('reconnecting');
        const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 16000);
        reconnectAttemptsRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      } else {
        setConnectionStatus('disconnected');
      }
    };

    ws.onerror = () => {
      // Error will be followed by onclose
    };
  }, [enabled, getWsUrl, queryClient, onTelemetryUpdate]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, []);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  // Connect on mount and when enabled changes
  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    connectionStatus,
    lastMessage,
    sendMessage,
  };
}