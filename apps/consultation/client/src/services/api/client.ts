declare global {
  interface Window {
    __MCS_API_BASE__?: string;
  }
}

export type SessionPersistenceMode = "local" | "session";

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "[::1]"]);
const SESSION_TOKEN_STORAGE_KEY = "mcs_session_token";
const SESSION_PERSISTENCE_STORAGE_KEY = "mcs_session_persistence";
const FLOW_STATE_KEY_PREFIXES = [
  "mcs_consultation_session:",
  "mcs_assessment_session:",
];

function isLoopbackHost(hostname: string) {
  return LOOPBACK_HOSTS.has(hostname);
}

function normalizeApiBase(url: string) {
  try {
    const parsed = new URL(url, window.location.origin);

    if (!isLoopbackHost(window.location.hostname) && isLoopbackHost(parsed.hostname)) {
      parsed.hostname = window.location.hostname;
      parsed.protocol = window.location.protocol;
    }

    return parsed.toString().replace(/\/$/, "");
  } catch {
    return `${window.location.protocol}//${window.location.hostname}:18080/api/v1`;
  }
}

function getStorage(mode: SessionPersistenceMode) {
  return mode === "local" ? window.localStorage : window.sessionStorage;
}

function getStoredPersistenceMode(): SessionPersistenceMode {
  if (window.localStorage.getItem(SESSION_TOKEN_STORAGE_KEY)) {
    return "local";
  }

  if (window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY)) {
    return "session";
  }

  return window.localStorage.getItem(SESSION_PERSISTENCE_STORAGE_KEY) === "session" ? "session" : "local";
}

const API_BASE = normalizeApiBase(
  window.__MCS_API_BASE__ || `${window.location.protocol}//${window.location.hostname}:18080/api/v1`,
);

export function getSessionToken() {
  return (
    window.localStorage.getItem(SESSION_TOKEN_STORAGE_KEY) ||
    window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY)
  );
}

export function hasSessionToken() {
  return Boolean(getSessionToken());
}

export function getSessionPersistenceMode() {
  return getStoredPersistenceMode();
}

export function getSessionPersistencePreference() {
  return getStoredPersistenceMode() === "local";
}

export function setSessionPersistencePreference(keepLoggedIn: boolean) {
  window.localStorage.setItem(SESSION_PERSISTENCE_STORAGE_KEY, keepLoggedIn ? "local" : "session");
}

export function setSessionToken(token: string, options?: { persist?: boolean }) {
  const mode = options?.persist === false ? "session" : "local";
  window.localStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
  window.sessionStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
  getStorage(mode).setItem(SESSION_TOKEN_STORAGE_KEY, token);
  setSessionPersistencePreference(mode === "local");
}

export function clearSessionToken() {
  window.localStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
  window.sessionStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
}

function clearPersistedFlowState() {
  for (const storage of [window.localStorage, window.sessionStorage]) {
    for (const key of Object.keys(storage)) {
      if (FLOW_STATE_KEY_PREFIXES.some((prefix) => key.startsWith(prefix))) {
        storage.removeItem(key);
      }
    }
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getSessionToken();
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers,
    ...options,
  });

  let payload: any = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (response.status === 401) {
    clearSessionToken();
    clearPersistedFlowState();
  }

  if (!response.ok || payload.code !== 0) {
    const detail = payload.detail || payload;
    const validationMessage =
      Array.isArray(detail) && detail.length > 0
        ? detail
            .map((item) => {
              const loc = Array.isArray(item?.loc) ? item.loc.join(".") : "request";
              const msg = item?.msg || "invalid input";
              return `${loc}: ${msg}`;
            })
            .join("; ")
        : null;
    const message =
      detail.message ||
      payload.message ||
      validationMessage ||
      `Request failed (${response.status})`;
    throw new Error(message);
  }

  return (payload.data || {}) as T;
}
