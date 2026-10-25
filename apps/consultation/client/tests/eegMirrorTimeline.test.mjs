import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
const client = fileURLToPath(new URL("../", import.meta.url));
const output = mkdtempSync(join(tmpdir(), "eeg-mirror-timeline-"));
after(() => rmSync(output, { recursive: true, force: true }));
writeFileSync(join(output, "package.json"), '{"type":"module"}');
execFileSync(process.execPath, [
  join(client, "node_modules/typescript/bin/tsc"),
  join(client, "src/components/eeg/eegMirrorTimeline.ts"),
  "--outDir",
  output,
  "--rootDir",
  join(client, "src"),
  "--target",
  "ES2020",
  "--module",
  "ES2020",
  "--skipLibCheck",
  "--strict",
]);
const modulePath = join(output, "components/eeg/eegMirrorTimeline.js");
writeFileSync(
  modulePath,
  readFileSync(modulePath, "utf8").replace(
    '"./eegEmotionPresentation"',
    '"./eegEmotionPresentation.js"',
  ),
);
const { buildEegTimeline } = await import(pathToFileURL(modulePath));
const now = Date.parse("2026-10-22T08:00:00Z");
const window = (id, start, end, label, status = "ready") => ({
  sample_id: id,
  inference_id: id,
  turn_id: id,
  window_index: 1,
  prediction_status: status,
  primary_label: label,
  sample_started_at: new Date(now + start * 1000).toISOString(),
  sample_ended_at: new Date(now + end * 1000).toISOString(),
});

test("a sparse classification never fills the missing interval or extends to the present", () => {
  const result = buildEegTimeline(
    [window("a", -50, -40, "积极"), window("b", -20, -10, "中性")],
    now,
  );
  assert.equal(result.coverageMs, 20000);
  assert.equal(
    result.segments
      .filter((x) => x.label === null)
      .reduce((s, x) => s + x.end - x.start, 0),
    40000,
  );
  assert.equal(result.majority, "近期状态多变");
  assert.equal(result.segments.at(-1).label, null);
});
test("duration, rather than packet count, determines the recent majority", () => {
  const result = buildEegTimeline(
    [
      window("a", -60, -25, "消极"),
      window("b", -24, -20, "积极"),
      window("c", -19, -15, "积极"),
    ],
    now,
  );
  assert.equal(result.majority, "消极");
  assert.equal(result.coverageMs, 43000);
});
test("overlapping windows own each interval only once and turn-local indices may repeat", () => {
  const result = buildEegTimeline(
    [window("a", -40, -10, "消极"), window("b", -20, 0, "积极")],
    now,
  );
  assert.equal(result.coverageMs, 40000);
  assert.equal(
    result.segments
      .filter((x) => x.label === "消极")
      .reduce((s, x) => s + x.end - x.start, 0),
    20000,
  );
});
test("invalid, insufficient and future records remain unknown; a single result is still accumulating", () => {
  const result = buildEegTimeline(
    [
      window("a", -50, -40, "消极", "insufficient_frames"),
      window("b", 10, 20, "积极"),
      window("c", -30, -20, "中性"),
      window("d", -10, -5, "unknown"),
    ],
    now,
  );
  assert.equal(result.coverageMs, 10000);
  assert.equal(result.majority, "记录积累中");
});
