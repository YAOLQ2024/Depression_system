import { apiRequest } from "./client";
import type { UpdateUserProfilePayload, UserResponse } from "./contracts";

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
