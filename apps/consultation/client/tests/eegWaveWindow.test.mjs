import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

// Exercise the actual TypeScript module without adding a test framework to the application bundle.
const client = fileURLToPath(new URL("../", import.meta.url));
const output = mkdtempSync(join(tmpdir(), "eeg-wave-test-"));
after(() => rmSync(output, { recursive: true, force: true }));
writeFileSync(join(output, "package.json"), '{"type":"module"}');
execFileSync(process.execPath, [
  join(client, "node_modules/typescript/bin/tsc"),
  join(client, "src/components/eeg/eegWaveWindow.ts"),
  "--outDir", output, "--target", "ES2020", "--module", "ES2020", "--skipLibCheck", "--strict",
]);
const { EegWaveWindow, boundsFromExtrema, applyVerticalGain, formatWaveAxisValue } =
  await import(pathToFileURL(join(output, "eegWaveWindow.js")).href);

test("a longer initial snapshot cannot expand the four-second window or retain its old peak", () => {
  const stream = new EegWaveWindow(10);
  stream.reset([10000, ...Array(100).fill(2)]);
  assert.equal(stream.end - stream.start, 40);
  assert.equal(stream.sampleCount, 41);
  assert.deepEqual(stream.bounds, boundsFromExtrema(2, 2));
});

test("future peaks affect the range only as they become visible, including a fractional endpoint", () => {
  const stream = new EegWaveWindow(10);
  stream.reset(Array(41).fill(0));
  stream.append([0, 0, 0, 0, 100]);
  assert.deepEqual(stream.bounds, boundsFromExtrema(0, 0));
  stream.advance(400);
  assert.deepEqual(stream.bounds, boundsFromExtrema(0, 0));
  stream.advance(50);
  assert.deepEqual(stream.bounds, boundsFromExtrema(0, 50));
  stream.advance(50);
  assert.deepEqual(stream.bounds, boundsFromExtrema(0, 100));
});

test("an exiting peak contributes only its visible interpolation and then expires immediately", () => {
  const stream = new EegWaveWindow(10);
  stream.reset([100, ...Array(40).fill(0)]);
  stream.append([0]);
  stream.advance(50);
  assert.deepEqual(stream.bounds, boundsFromExtrema(0, 50));
  stream.advance(50);
  assert.deepEqual(stream.bounds, boundsFromExtrema(0, 0));
  assert.equal(stream.sampleCount, 41);
});

test("reset and delta-only startup discard previous scale and retained geometry", () => {
  const stream = new EegWaveWindow(10);
  stream.reset(Array(41).fill(1000));
  stream.takeSegmentChanges();
  stream.reset([]);
  stream.append([3, 4]);
  assert.deepEqual(stream.bounds, boundsFromExtrema(3, 4));
  assert.equal(stream.sampleCount, 2);
  assert.equal(stream.takeSegmentChanges().clear, true);
});

test("empty, invalid, one-point, constant and offset signals have valid, readable ranges", () => {
  for (const values of [[], [NaN, Infinity], [5], Array(41).fill(100), [-9, -8], [3, NaN, 4]]) {
    const stream = new EegWaveWindow(10);
    stream.reset(values);
    const { lowerBound, upperBound } = stream.bounds;
    assert.ok(Number.isFinite(lowerBound) && Number.isFinite(upperBound) && upperBound > lowerBound);
    assert.notEqual(formatWaveAxisValue(lowerBound, upperBound - lowerBound), formatWaveAxisValue(upperBound, upperBound - lowerBound));
    for (const value of values.filter(Number.isFinite)) assert.ok(value >= lowerBound && value <= upperBound);
  }
  const stream = new EegWaveWindow(10);
  stream.reset([3, NaN, 4]);
  assert.ok(stream.bounds.lowerBound > 0, "invalid values must not insert a fake zero");
  assert.equal(stream.takeSegmentChanges().changed[0].path, "M0 3M2 4");
});

test("range and gain changes preserve retained path geometry", () => {
  const stream = new EegWaveWindow(10);
  stream.reset(Array(41).fill(1));
  stream.takeSegmentChanges();
  stream.append([8]);
  stream.takeSegmentChanges();
  stream.advance(100);
  const automatic = stream.bounds;
  const gained = applyVerticalGain(automatic, 2);
  assert.equal(gained.upperBound - gained.lowerBound, (automatic.upperBound - automatic.lowerBound) / 2);
  assert.deepEqual(stream.takeSegmentChanges(), { clear: false, changed: [], removed: [] });
});

test("append touches only the current segment and new segments, preserving boundary connections", () => {
  const stream = new EegWaveWindow(256);
  stream.reset(Array(1025).fill(1));
  stream.takeSegmentChanges();
  stream.append(Array(31).fill(2));
  const changes = stream.takeSegmentChanges();
  assert.equal(changes.clear, false);
  assert.equal(changes.changed.length, 1);
  assert.equal(changes.changed[0].id, 16);
  assert.ok(changes.changed[0].path.startsWith("M0 1L1 1L2 2"));
});

test("extended streaming and large bursts keep data, geometry and catch-up bounded", () => {
  const stream = new EegWaveWindow(256);
  stream.reset(Array(1025).fill(0));
  for (let batch = 0; batch < 5000; batch++) {
    stream.append(Array.from({ length: 31 }, (_, index) => Math.sin((batch * 31 + index) / 20)));
    stream.advance(31 / 256 * 1000);
    stream.takeSegmentChanges();
    assert.ok(stream.sampleCount <= 1026);
    assert.ok(stream.segmentCount <= 18);
  }
  stream.append(Array(100000).fill(7));
  assert.ok(stream.sampleCount <= 1024 + 128 + 2);
  assert.ok(stream.segmentCount <= 20);
  stream.advance(500);
  assert.equal(stream.pending, false);
  assert.deepEqual(stream.bounds, boundsFromExtrema(7, 7));
});

test("sliding extrema match an independent visible-window scan across arbitrary packets and fractional frames", () => {
  const rate = 32;
  const stream = new EegWaveWindow(rate);
  const all = Array.from({ length: 129 }, (_, index) => Math.sin(index) * 10);
  stream.reset(all);
  let seed = 921;
  const random = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
  const at = (position) => {
    const left = Math.floor(position);
    if (left === position) return all[left];
    if (!Number.isFinite(all[left]) || !Number.isFinite(all[left + 1])) return NaN;
    return all[left] + (all[left + 1] - all[left]) * (position - left);
  };
  for (let frame = 0; frame < 2000; frame++) {
    if (frame % 3 === 0) {
      const packet = Array.from({ length: 1 + Math.floor(random() * 14) }, () => random() < 0.03 ? NaN : (random() - 0.5) * 100);
      all.push(...packet);
      stream.append(packet);
    }
    stream.advance(10 + random() * 80);
    const visible = [at(stream.start), at(stream.end), ...all.slice(Math.max(0, Math.ceil(stream.start)), Math.floor(stream.end) + 1)].filter(Number.isFinite);
    assert.deepEqual(stream.bounds, boundsFromExtrema(Math.min(...visible), Math.max(...visible)), `frame ${frame}`);
    stream.takeSegmentChanges();
  }
});
