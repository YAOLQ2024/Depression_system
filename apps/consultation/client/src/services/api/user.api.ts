import { apiRequest } from "./client";
import type {
  PreparationStateResponse,
  UpdateUserPreparationStatePayload,
  UpdateUserProfilePayload,
  UserResponse,
} from "./contracts";

export async function getCurrentUser() {
  const data = await apiRequest<UserResponse>("/users/me", { method: "GET" });
  return data.user;
}

export async function updateCurrentUserProfile(payload: UpdateUserProfilePayload) {
  const data = await apiRequest<UserResponse>("/users/me/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  return data.user;
}

export async function getCurrentUserPreparationState() {
  const data = await apiRequest<PreparationStateResponse>("/users/me/preparation-state", {
    method: "GET",
  });
  return data.preparation_state;
}

export async function updateCurrentUserPreparationState(payload: UpdateUserPreparationStatePayload) {
  const data = await apiRequest<PreparationStateResponse>("/users/me/preparation-state", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  return data.user || null;
}
