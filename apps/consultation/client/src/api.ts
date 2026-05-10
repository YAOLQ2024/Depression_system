declare global {
  interface Window {
    __MCS_API_BASE__?: string;
  }
}

const API_BASE = window.__MCS_API_BASE__ || "http://127.0.0.1:8080/api/v1";
const SESSION_TOKEN_STORAGE_KEY = "mcs_session_token";

export function getSessionToken() {
  return window.localStorage.getItem(SESSION_TOKEN_STORAGE_KEY);
}

export function setSessionToken(token: string) {
  window.localStorage.setItem(SESSION_TOKEN_STORAGE_KEY, token);
}

export function clearSessionToken() {
  window.localStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getSessionToken();
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload: any = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (!response.ok || payload.code !== 0) {
    const detail = payload.detail || payload;
    const message = detail.message || payload.message || `Request failed (${response.status})`;
    throw new Error(message);
  }

  return (payload.data || {}) as T;
}
