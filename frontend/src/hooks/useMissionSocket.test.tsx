import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../lib/demoSession', () => ({
  getDemoSessionId: () => 'socket-session-123',
}));

import { useMissionSocket } from './useMissionSocket';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;

  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
    queueMicrotask(() => {
      this.onopen?.();
    });
  }

  close() {
    this.onclose?.();
  }

  send() {}

  emitMessage(message: unknown) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }
}

describe('useMissionSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  it('invalidates mission state and forwards telemetry updates', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: Infinity },
        mutations: { gcTime: Infinity },
      },
    });
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries');
    const onTelemetryUpdate = vi.fn();

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    renderHook(() => useMissionSocket({ onTelemetryUpdate }), { wrapper });

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });
    expect(MockWebSocket.instances[0].url).toContain(
      '/api/ws/mission?session_id=socket-session-123'
    );

    act(() => {
      MockWebSocket.instances[0].emitMessage({
        event: 'telemetry.updated',
        payload: {
          mission_id: 'luna-mission-001',
          elapsed_s: 296,
          resources: {
            battery_pct: 26,
            storage_pct: 100,
            temperature_c: -25.2,
            comm_window_remaining_s: 6904,
            op_time_remaining_s: 28504,
          },
          timestamp: '2026-08-20T12:00:00.000Z',
        },
      });
    });

    await waitFor(() => {
      expect(onTelemetryUpdate).toHaveBeenCalledTimes(1);
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ['mission', 'socket-session-123', 'state'],
        refetchType: 'active',
      });
    });
  });
});
