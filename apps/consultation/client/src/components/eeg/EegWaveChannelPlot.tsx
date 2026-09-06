import { useEffect, useRef } from "react";

import { applyVerticalGain, EEG_WINDOW_SECONDS, EegWaveWindow, formatWaveAxisValue } from "./eegWaveWindow";

type SampleMeta = { length: number; lastSeq: number | null; lastCapturedAtMs: number | null };
type Props = {
  appendMeta: SampleMeta;
  appendValues: number[];
  color: string;
  fullMeta: SampleMeta;
  fullValues: number[];
  label: string;
  reset: boolean;
  samplingRate: number;
  verticalGain: number;
};

const SVG_NS = "http://www.w3.org/2000/svg";
const FRAME_INTERVAL_MS = 50;
const PADDING_Y = 10;

function sameMeta(left: SampleMeta | null, right: SampleMeta) {
  return left?.length === right.length && left.lastSeq === right.lastSeq && left.lastCapturedAtMs === right.lastCapturedAtMs;
}

/** React owns the shell. Streaming updates retain SVG paths and change only their coordinate transform. */
export function EegWaveChannelPlot(props: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const viewportRef = useRef<SVGSVGElement>(null);
  const pathsRef = useRef<SVGGElement>(null);
  const upperRef = useRef<HTMLSpanElement>(null);
  const lowerRef = useRef<HTMLSpanElement>(null);
  const controllerRef = useRef<{ update: (next: Props) => void } | null>(null);

  useEffect(() => {
    const svg = svgRef.current;
    const viewport = viewportRef.current;
    const paths = pathsRef.current;
    if (!svg || !viewport || !paths) return;
    const rate = Number.isFinite(props.samplingRate) && props.samplingRate > 0 ? props.samplingRate : 256;
    const stream = new EegWaveWindow(rate);
    const elements = new Map<number, SVGPathElement>();
    let fullMeta: SampleMeta | null = null;
    let appendMeta: SampleMeta | null = null;
    let lastReset = false;
    let gain = 1;
    let width = 1;
    let plotHeight = 1;
    let frameId: number | null = null;
    let lastFrameAt = performance.now();

    const render = () => {
      const changes = stream.takeSegmentChanges();
      if (changes.clear) { paths.replaceChildren(); elements.clear(); }
      for (const id of changes.removed) { elements.get(id)?.remove(); elements.delete(id); }
      for (const segment of changes.changed) {
        let path = elements.get(segment.id);
        if (!path) {
          path = document.createElementNS(SVG_NS, "path");
          path.setAttribute("fill", "none");
          path.setAttribute("stroke", "currentColor");
          path.setAttribute("stroke-width", "1.7");
          path.setAttribute("stroke-linejoin", "round");
          path.setAttribute("vector-effect", "non-scaling-stroke");
          path.setAttribute("transform", `translate(${segment.start} 0)`);
          paths.appendChild(path);
          elements.set(segment.id, path);
        }
        path.setAttribute("d", segment.path);
      }
      const bounds = applyVerticalGain(stream.bounds, gain);
      const span = bounds.upperBound - bounds.lowerBound;
      const xScale = width / stream.sampleSpan;
      const yScale = plotHeight / span;
      paths.setAttribute("transform", `matrix(${xScale} 0 0 ${-yScale} ${-stream.start * xScale} ${bounds.upperBound * yScale})`);
      // Both labels and the transform are committed together, before the browser paints.
      const upper = `${formatWaveAxisValue(bounds.upperBound, span)} μV`;
      const lower = `${formatWaveAxisValue(bounds.lowerBound, span)} μV`;
      if (upperRef.current && upperRef.current.textContent !== upper) upperRef.current.textContent = upper;
      if (lowerRef.current && lowerRef.current.textContent !== lower) lowerRef.current.textContent = lower;
    };

    const drawFrame = (now: number) => {
      frameId = null;
      const elapsed = now - lastFrameAt;
      if (elapsed < FRAME_INTERVAL_MS) { frameId = requestAnimationFrame(drawFrame); return; }
      lastFrameAt = now;
      stream.advance(elapsed);
      render();
      if (stream.pending) frameId = requestAnimationFrame(drawFrame);
    };
    const schedule = () => {
      if (frameId === null) {
        lastFrameAt = performance.now();
        frameId = requestAnimationFrame(drawFrame);
      }
    };

    controllerRef.current = {
      update(next) {
        const fullChanged = !sameMeta(fullMeta, next.fullMeta);
        const resetChanged = next.reset && !lastReset;
        let changed = gain !== next.verticalGain;
        if (fullChanged || resetChanged) {
          stream.reset(next.fullValues);
          fullMeta = next.fullMeta;
          // A reset can contain only a delta, with no full snapshot.
          if (!next.fullValues.length && next.appendValues.length) stream.append(next.appendValues);
          appendMeta = next.appendMeta;
          changed = true;
        } else if (!sameMeta(appendMeta, next.appendMeta)) {
          stream.append(next.appendValues);
          appendMeta = next.appendMeta;
          changed = next.appendValues.length > 0 || changed;
        }
        lastReset = next.reset;
        gain = next.verticalGain;
        if (changed) schedule();
      },
    };

    const resize = () => {
      const rect = svg.getBoundingClientRect();
      width = Math.max(1, rect.width);
      plotHeight = Math.max(1, rect.height - PADDING_Y * 2);
      viewport.setAttribute("height", String(plotHeight));
      schedule();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(svg);
    resize();
    return () => {
      observer.disconnect();
      if (frameId !== null) cancelAnimationFrame(frameId);
      paths.replaceChildren();
      controllerRef.current = null;
    };
  }, [props.samplingRate]);

  useEffect(() => { controllerRef.current?.update(props); }, [props]);

  return (
    <div className="relative h-full overflow-hidden rounded-[10px] border border-white/8 bg-slate-900">
      <svg ref={svgRef} className="block h-full w-full" style={{ color: props.color }} role="img" aria-label={`${props.label} 脑电波形，最近${EEG_WINDOW_SECONDS}秒`}>
        <svg ref={viewportRef} x="0" y={PADDING_Y} width="100%" height="1" overflow="hidden">
          <line x1="0" x2="100%" y1="0" y2="0" stroke="rgba(148,163,184,0.18)" />
          <line x1="0" x2="100%" y1="50%" y2="50%" stroke="rgba(148,163,184,0.12)" strokeDasharray="5 7" />
          <line x1="0" x2="100%" y1="100%" y2="100%" stroke="rgba(148,163,184,0.18)" />
          <g ref={pathsRef} />
        </svg>
      </svg>
      <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-slate-950/45 to-transparent" />
      <span ref={upperRef} className="pointer-events-none absolute right-2 top-1 text-[9px] font-medium tabular-nums text-slate-400" />
      <span ref={lowerRef} className="pointer-events-none absolute right-2 bottom-[2px] text-[9px] font-medium tabular-nums text-slate-400" />
      <div className="pointer-events-none absolute left-2 top-1 text-[9px] font-semibold text-slate-200">{props.label}</div>
    </div>
  );
}
