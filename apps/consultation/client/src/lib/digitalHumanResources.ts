import { useSyncExternalStore } from "react";

const PORTRAIT_QUERY = "(orientation: portrait)";
const ROOT = "/digital-human/portrait-male-v1";
const folders: Record<string, string> = {
  "consultation-v1": "问诊（consultation-v1）",
  "result-v1": "结果页",
  "intervention-v1": "调节干预入口",
};
const consultationNames = new Set([
  "greeting-001", "handoff-001", "chief-complaint-001", "chief-complaint-001-else",
  "chief-complaint-002", "chief-complaint-003", "symptom-screening-001",
  "symptom-screening-002", "symptom-screening-003", "risk-screening-001",
  "risk-screening-002", "risk-screening-003", "risk-screening-004", "risk-screening-005",
  "risk-screening-review-001", "risk-screening-review-002",
]);
const resultNames = new Set([
  "result-intro-001", "result-severity-none-001", "result-severity-mild-001",
  "result-severity-moderate-001", "result-severity-severe-001",
]);

function subscribeOrientation(listener: () => void) {
  const media = window.matchMedia(PORTRAIT_QUERY);
  media.addEventListener("change", listener);
  return () => media.removeEventListener("change", listener);
}
export function usePortraitOrientation() {
  return useSyncExternalStore(subscribeOrientation, () => window.matchMedia(PORTRAIT_QUERY).matches, () => false);
}

/** Keep logical node URLs unchanged; resolve only the file presented by the player. */
export function resolveDigitalHumanSource(source: string, portrait: boolean): string {
  if (!portrait) return source;
  const path = source.split(/[?#]/, 1)[0];
  const match = path.match(/^\/digital-human\/(consultation-v1|scale-assessment-v1|result-v1|intervention-v1)\/([^/]+)\.webm$/);
  if (!match) return source;
  const [, family, name] = match;
  let folder = folders[family];
  if (family === "consultation-v1" && !consultationNames.has(name)) return source;
  if (family === "result-v1" && !resultNames.has(name)) return source;
  if (family === "intervention-v1" && name !== "intervention-entry-001") return source;
  if (family === "scale-assessment-v1") {
    if (name === "answer-option-reminder-001") folder = "量表通用提示（在需要重新提示选项时播放）";
    else {
      const item = name.match(/^(phq9|sds|sas|social-function)-(\d{3})$/);
      if (!item) return source;
      const index = Number(item[2]);
      const limits: Record<string, [number, number, string]> = {
        phq9: [1, 9, "PHQ-9"], sds: [1, 20, "SDS"], sas: [1, 20, "SAS"],
        "social-function": [0, 10, "社会功能缺陷量表"],
      };
      const [first, last, itemFolder] = limits[item[1]];
      if (index < first || index > last) return source;
      folder = itemFolder;
    }
  }
  // Landscape clip trims are tied to the old recording's timing, not the new actor.
  return encodeURI(`${ROOT}/${folder}/${name}.webm`);
}

export function getDigitalHumanLayout(source: string, portrait: boolean) {
  const resolved = resolveDigitalHumanSource(source, portrait);
  // This clip is a documented temporary copy of the landscape actor.
  return resolved.startsWith(ROOT) && !resolved.endsWith("/risk-screening-003.webm") ? "portrait" : "landscape";
}

export function getClipPlaybackEnd(source: string, duration: number) {
  const end = source.match(/#t=[\d.]*,([\d.]+)/)?.[1];
  return end ? Math.min(Number(end), duration) : duration;
}
