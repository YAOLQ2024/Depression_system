import { apiRequest } from "./client";
import type { AuthLoginRequest, AuthLoginResponse, AuthRegisterRequest } from "./contracts";

export function login(payload: AuthLoginRequest) {
  return apiRequest<AuthLoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function register(payload: AuthRegisterRequest) {
  return apiRequest<Record<string, never>>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logout() {
  await apiRequest<Record<string, never>>("/auth/logout", { method: "POST" });
}
