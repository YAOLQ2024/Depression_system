import type { EegWindowRecord } from "./eegMirrorTypes";
import {
  coerceEegEmotionLabel,
  type EegEmotionLabel,
} from "./eegEmotionPresentation";

export type EegTimelineSegment = {
  start: number;
  end: number;
  label: EegEmotionLabel | null;
};
export function buildEegTimeline(
  windows: EegWindowRecord[],
  now: number,
  spanMs = 60000,
) {
  const start = now - spanMs;
  const valid = windows.flatMap((item) => {
    const a = Date.parse(item.sample_started_at || ""),
      b = Date.parse(item.sample_ended_at || "");
    const label = coerceEegEmotionLabel(item.primary_label);
    return item.prediction_status === "ready" &&
      label &&
      Number.isFinite(a) &&
      Number.isFinite(b) &&
      b > a &&
      b > start &&
      a < now
      ? [
          {
            start: Math.max(start, a),
            end: Math.min(now, b),
            label,
            id: item.sample_id,
          },
        ]
      : [];
  });
  const boundaries = [
    ...new Set([start, now, ...valid.flatMap((v) => [v.start, v.end])]),
  ].sort((a, b) => a - b);
  const segments: EegTimelineSegment[] = [];
  const durations = new Map<EegEmotionLabel, number>();
  for (let i = 1; i < boundaries.length; i++) {
    const a = boundaries[i - 1],
      b = boundaries[i];
    // Newer windows own overlapping intervals; one interval is never counted twice.
    const owner = valid
      .filter((v) => v.start < b && v.end > a)
      .sort((x, y) => y.start - x.start || y.end - x.end)[0];
    const label = owner?.label || null;
    segments.push({ start: a, end: b, label });
    if (label) durations.set(label, (durations.get(label) || 0) + b - a);
  }
  const sorted = [...durations].sort((a, b) => b[1] - a[1]);
  const majority =
    new Set(valid.map((v) => v.id)).size < 2
      ? "记录积累中"
      : sorted.length > 1 && sorted[0][1] === sorted[1][1]
        ? "近期状态多变"
        : sorted[0]?.[0] || "记录积累中";
  return {
    segments,
    coverageMs: [...durations.values()].reduce((a, b) => a + b, 0),
    majority,
  };
}
