export const EEG_WINDOW_SECONDS = 4;
export const EEG_VERTICAL_GAIN_MIN = 0.25;
export const EEG_VERTICAL_GAIN_MAX = 32;
export const EEG_HORIZONTAL_GAIN_MIN = 1;
export const EEG_HORIZONTAL_GAIN_MAX = 8;
const SEGMENT_SAMPLES = 64;
const MAX_PENDING_SECONDS = 0.5;
const MIN_SPAN_UV = 0.1;

export type EegWaveBounds = { lowerBound: number; upperBound: number };
export type WaveSegment = { id: number; start: number; end: number; path: string; penDown: boolean };

export function formatWaveAxisValue(value: number, span: number) {
  if (!Number.isFinite(value)) return "--";
  // Precision follows the range, so a small signal with a large offset still has distinct labels.
  const decimals = Math.min(6, Math.max(0, Math.ceil(-Math.log10(span / 100))));
  const formatted = value.toFixed(decimals);
  return Number(formatted) === 0 ? (0).toFixed(decimals) : formatted;
}

export function applyVerticalGain(bounds: EegWaveBounds, gain: number): EegWaveBounds {
  const center = bounds.lowerBound / 2 + bounds.upperBound / 2;
  const safeGain = Math.min(EEG_VERTICAL_GAIN_MAX, Math.max(EEG_VERTICAL_GAIN_MIN, gain));
  const halfSpan = (bounds.upperBound - bounds.lowerBound) / safeGain / 2;
  return { lowerBound: center - halfSpan, upperBound: center + halfSpan };
}

// Stateless rounding: an expired peak cannot keep the range enlarged through hysteresis.
export function boundsFromExtrema(min: number, max: number): EegWaveBounds {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return { lowerBound: -1, upperBound: 1 };
  const center = min / 2 + max / 2;
  const span = Math.max(MIN_SPAN_UV, max - min);
  const padding = span * 0.08;
  const step = 10 ** Math.floor(Math.log10(span)) / 10;
  return {
    lowerBound: Math.floor((center - span / 2 - padding) / step) * step,
    upperBound: Math.ceil((center + span / 2 + padding) / step) * step,
  };
}

class ExtremeQueue {
  private points: { index: number; value: number }[] = [];
  private head = 0;
  constructor(private readonly minimum: boolean) {}

  push(index: number, value: number) {
    while (this.points.length > this.head) {
      const last = this.points[this.points.length - 1].value;
      if (this.minimum ? last < value : last > value) break;
      this.points.pop();
    }
    this.points.push({ index, value });
  }

  expire(firstIndex: number) {
    while (this.head < this.points.length && this.points[this.head].index < firstIndex) this.head++;
    if (this.head > 256 && this.head * 2 >= this.points.length) {
      this.points = this.points.slice(this.head);
      this.head = 0;
    }
  }

  get value() { return this.points[this.head]?.value; }
}

/** Bounded streaming data and retained path segments. Only visible samples enter the extrema queues. */
export class EegWaveWindow {
  readonly sampleSpan: number;
  private readonly maxPendingSamples: number;
  private viewSampleSpan: number;
  private samples = new Map<number, number>();
  private segments = new Map<number, WaveSegment>();
  private changedSegments = new Map<number, WaveSegment>();
  private removedSegments = new Set<number>();
  private clearSegments = false;
  private minimum = new ExtremeQueue(true);
  private maximum = new ExtremeQueue(false);
  private nextIndex = 0;
  private scannedThrough = -1;
  private cursor = -1;

  constructor(readonly samplingRate: number) {
    this.sampleSpan = Math.max(1, Math.round(samplingRate * EEG_WINDOW_SECONDS));
    this.viewSampleSpan = this.sampleSpan;
    this.maxPendingSamples = Math.max(1, Math.round(samplingRate * MAX_PENDING_SECONDS));
  }

  get end() { return this.cursor; }
  get start() { return this.cursor - this.viewSampleSpan; }
  get visibleSampleSpan() { return this.viewSampleSpan; }
  get pending() { return this.cursor < this.nextIndex - 1; }
  get sampleCount() { return this.samples.size; }
  get segmentCount() { return this.segments.size; }

  /** Horizontal zoom changes the actual visible time window, so extrema must follow it too. */
  setVisibleSampleSpan(sampleSpan: number) {
    const nextSpan = Math.min(this.sampleSpan, Math.max(1, Math.round(sampleSpan)));
    if (nextSpan === this.viewSampleSpan) return;
    this.viewSampleSpan = nextSpan;
    this.rebuildExtrema();
  }

  reset(values: number[]) {
    this.samples.clear();
    this.segments.clear();
    this.changedSegments.clear();
    this.removedSegments.clear();
    this.clearSegments = true;
    this.minimum = new ExtremeQueue(true);
    this.maximum = new ExtremeQueue(false);
    this.nextIndex = 0;
    this.scannedThrough = -1;
    this.cursor = -1;
    // Oversized snapshots must not change the configured window duration.
    this.append(values.slice(-(this.sampleSpan + 1)));
    this.moveTo(this.nextIndex - 1);
  }

  append(values: number[]) {
    if (!values.length) return;
    const wasEmpty = this.nextIndex === 0;
    // Bound burst processing too; omitted history is already outside the display and pending windows.
    const capacity = this.sampleSpan + this.maxPendingSamples + 2;
    const skip = Math.max(0, values.length - capacity);
    this.nextIndex += skip;
    for (let offset = skip; offset < values.length; offset++) {
      const index = this.nextIndex++;
      const value = values[offset];
      const id = Math.floor(index / SEGMENT_SAMPLES);
      let segment = this.segments.get(id);
      if (!segment) {
        const previous = this.samples.get(index - 1);
        const connected = previous !== undefined && Number.isFinite(previous);
        segment = {
          id, start: connected ? index - 1 : index, end: index,
          path: connected ? `M0 ${previous}` : "", penDown: connected,
        };
        this.segments.set(id, segment);
      }
      if (Number.isFinite(value)) {
        segment.path += `${segment.penDown ? "L" : "M"}${index - segment.start} ${value}`;
        segment.penDown = true;
      } else {
        segment.penDown = false;
      }
      segment.end = index;
      this.changedSegments.set(id, segment);
      this.samples.set(index, value);
    }
    const latest = this.nextIndex - 1;
    this.moveTo(wasEmpty ? latest : Math.max(this.cursor, latest - this.maxPendingSamples));
  }

  advance(elapsedMs: number) {
    this.moveTo(Math.min(this.nextIndex - 1, this.cursor + Math.max(0, elapsedMs) * this.samplingRate / 1000));
  }

  private moveTo(end: number) {
    this.cursor = end;
    const first = Math.ceil(this.start);
    const last = Math.floor(end);
    // On a large catch-up, skip expired history instead of scanning a gap in the stream.
    for (let index = Math.max(this.scannedThrough + 1, first, 0); index <= last; index++) {
      const value = this.samples.get(index);
      if (value !== undefined && Number.isFinite(value)) {
        this.minimum.push(index, value);
        this.maximum.push(index, value);
      }
    }
    this.scannedThrough = last;
    this.minimum.expire(first);
    this.maximum.expire(first);
    // Retain the full default window so horizontal zoom can return to four seconds without history.
    const retainedStart = Math.floor(this.cursor - this.sampleSpan);
    for (const index of this.samples.keys()) {
      if (index >= retainedStart) break;
      this.samples.delete(index);
    }
    for (const [id, segment] of this.segments) {
      if (segment.end >= retainedStart) break;
      this.segments.delete(id);
      this.changedSegments.delete(id);
      this.removedSegments.add(id);
    }
  }

  private rebuildExtrema() {
    this.minimum = new ExtremeQueue(true);
    this.maximum = new ExtremeQueue(false);
    const first = Math.ceil(this.start);
    const last = Math.floor(this.end);
    for (let index = Math.max(0, first); index <= last; index++) {
      const value = this.samples.get(index);
      if (value !== undefined && Number.isFinite(value)) {
        this.minimum.push(index, value);
        this.maximum.push(index, value);
      }
    }
    this.scannedThrough = last;
  }

  private valueAt(position: number) {
    const left = Math.floor(position);
    const leftValue = this.samples.get(left);
    if (leftValue === undefined || !Number.isFinite(leftValue)) return undefined;
    if (position === left) return leftValue;
    const rightValue = this.samples.get(left + 1);
    if (rightValue === undefined || !Number.isFinite(rightValue)) return undefined;
    return leftValue + (rightValue - leftValue) * (position - left);
  }

  get bounds(): EegWaveBounds {
    let min = this.minimum.value ?? Infinity;
    let max = this.maximum.value ?? -Infinity;
    // Fractional endpoints must match the clipped path, not include the entire outside sample.
    for (const value of [this.valueAt(this.start), this.valueAt(this.end)]) {
      if (value !== undefined) { min = Math.min(min, value); max = Math.max(max, value); }
    }
    return boundsFromExtrema(min, max);
  }

  takeSegmentChanges() {
    const changes = {
      clear: this.clearSegments,
      changed: [...this.changedSegments.values()],
      removed: [...this.removedSegments],
    };
    this.clearSegments = false;
    this.changedSegments.clear();
    this.removedSegments.clear();
    return changes;
  }
}
