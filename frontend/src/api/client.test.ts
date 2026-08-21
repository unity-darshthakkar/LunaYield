import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('apiClient session scoping', () => {
  beforeEach(() => {
    vi.resetModules();
    window.sessionStorage.clear();
  });

  it('adds the demo session header to outgoing requests', async () => {
    const requestUse = vi.fn();

    vi.doMock('axios', () => ({
      default: {
        create: vi.fn(() => ({
          interceptors: {
            request: { use: requestUse },
            response: { use: vi.fn() },
          },
        })),
      },
    }));

    vi.doMock('../lib/demoSession', () => ({
      getDemoSessionId: () => 'session-header-test',
    }));

    await import('./client');

    expect(requestUse).toHaveBeenCalledTimes(1);
    const requestInterceptor = requestUse.mock.calls[0][0] as (
      config: { headers?: Record<string, string> }
    ) => { headers: Record<string, string> };

    const config = requestInterceptor({ headers: {} });

    expect(config.headers['X-Demo-Session-Id']).toBe('session-header-test');
  });
});
