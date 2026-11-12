import { useSyncExternalStore } from "react";

export * from "./digitalHumanSources";

const PORTRAIT_QUERY = "(orientation: portrait)";
function subscribeOrientation(listener: () => void) {
  const media = window.matchMedia(PORTRAIT_QUERY);
  media.addEventListener("change", listener);
  return () => media.removeEventListener("change", listener);
}
export function usePortraitOrientation() {
  return useSyncExternalStore(subscribeOrientation, () => window.matchMedia(PORTRAIT_QUERY).matches, () => false);
}
