import { apiRequest } from "./client";
import type { BootstrapResponse } from "./contracts";

export function getBootstrapSummary() {
  return apiRequest<BootstrapResponse>("/system/bootstrap", { method: "GET" });
}
