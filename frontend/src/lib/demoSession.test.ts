import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  DEMO_SESSION_STORAGE_KEY,
  getDemoSessionId,
} from './demoSession';

describe('demoSession', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('creates a session ID once when missing', () => {
    const randomUuidSpy = vi
      .spyOn(window.crypto, 'randomUUID')
      .mockReturnValue('session-a');

    const sessionId = getDemoSessionId();

    expect(sessionId).toBe('session-a');
    expect(window.sessionStorage.getItem(DEMO_SESSION_STORAGE_KEY)).toBe('session-a');
    expect(randomUuidSpy).toHaveBeenCalledTimes(1);
  });

  it('reuses the existing session ID in the same tab', () => {
    window.sessionStorage.setItem(DEMO_SESSION_STORAGE_KEY, 'session-existing');
    const randomUuidSpy = vi.spyOn(window.crypto, 'randomUUID');

    const firstSessionId = getDemoSessionId();
    const secondSessionId = getDemoSessionId();

    expect(firstSessionId).toBe('session-existing');
    expect(secondSessionId).toBe('session-existing');
    expect(randomUuidSpy).not.toHaveBeenCalled();
  });
});
