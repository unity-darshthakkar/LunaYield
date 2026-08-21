export const DEMO_SESSION_STORAGE_KEY = 'lunayield_demo_session_id';

export function getDemoSessionId(): string {
  const existingSessionId = window.sessionStorage.getItem(DEMO_SESSION_STORAGE_KEY);
  if (existingSessionId) {
    return existingSessionId;
  }

  const sessionId = window.crypto.randomUUID();
  window.sessionStorage.setItem(DEMO_SESSION_STORAGE_KEY, sessionId);
  return sessionId;
}
