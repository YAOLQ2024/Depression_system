import {
  memo,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import { Minus, Plus, RotateCcw } from "lucide-react";
import type { EegWaveSample } from "../../types";
import { EegWaveChannelPlot } from "./EegWaveChannelPlot";
import {
  EEG_HORIZONTAL_GAIN_MAX,
  EEG_HORIZONTAL_GAIN_MIN,
  EEG_WINDOW_SECONDS,
  EEG_VERTICAL_GAIN_MIN,
  EEG_VERTICAL_GAIN_MAX,
} from "./eegWaveWindow";

const EEG_CHANNEL_COLORS = ["#60a5fa", "#34d399", "#f59e0b"];

type EegWaveSampleMeta = {
  length: number;
  lastSeq: number | null;
  lastCapturedAtMs: number | null;
};

function clampNumber(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function parseCapturedAtTimestamp(value?: string | null) {
  if (!value) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function extractEegWaveSampleMeta(samples: EegWaveSample[]): EegWaveSampleMeta {
  const lastSample =
    samples.length > 0 ? samples[samples.length - 1] : undefined;
  return {
    length: samples.length,
    lastSeq: typeof lastSample?.seq === "number" ? lastSample.seq : null,
    lastCapturedAtMs: parseCapturedAtTimestamp(lastSample?.captured_at),
  };
}

function areEegWaveSampleMetasEqual(
  left: EegWaveSampleMeta,
  right: EegWaveSampleMeta,
) {
  return (
    left.length === right.length &&
    left.lastSeq === right.lastSeq &&
    left.lastCapturedAtMs === right.lastCapturedAtMs
  );
}

function areChannelNamesEqual(left: string[], right: string[]) {
  if (left.length !== right.length) {
    return false;
  }
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) {
      return false;
    }
  }
  return true;
}

function extractChannelValues(samples: EegWaveSample[], channelIndex: number) {
  return samples.map((sample) => {
    const value = sample.values?.[channelIndex];
    return typeof value === "number" && Number.isFinite(value)
      ? value
      : Number.NaN;
  });
}

type EegWavePreviewProps = {
  appendSamples: EegWaveSample[];
  channelNames: string[];
  reset: boolean;
  samples: EegWaveSample[];
  samplingRate: number;
};

export const EegWavePreview = memo(
  function EegWavePreview({
    appendSamples,
    channelNames,
    reset,
    samples,
    samplingRate,
  }: EegWavePreviewProps) {
    const [horizontalGain, setHorizontalGain] = useState(1);
    const [verticalGain, setVerticalGain] = useState(1);
    const activePointersRef = useRef(
      new Map<number, { x: number; y: number }>(),
    );
    const pinchDistanceRef = useRef<number | null>(null);
    const pinchGainRef = useRef(1);
    const visibleChannelNames = useMemo(
      () => ["Fpz", "T7", "T8"].filter((name) => channelNames.includes(name)),
      [channelNames],
    );
    const fullMeta = useMemo(
      () => extractEegWaveSampleMeta(samples),
      [samples],
    );
    const appendMeta = useMemo(
      () => extractEegWaveSampleMeta(appendSamples),
      [appendSamples],
    );
    const fullChannelValues = useMemo(
      () =>
        visibleChannelNames.map((name) =>
          extractChannelValues(samples, channelNames.indexOf(name)),
        ),
      [samples, visibleChannelNames],
    );
    const appendChannelValues = useMemo(
      () =>
        visibleChannelNames.map((name) =>
          extractChannelValues(appendSamples, channelNames.indexOf(name)),
        ),
      [appendSamples, visibleChannelNames],
    );

    const updateVerticalGain = (nextGain: number) => {
      setVerticalGain(
        clampNumber(nextGain, EEG_VERTICAL_GAIN_MIN, EEG_VERTICAL_GAIN_MAX),
      );
    };

    const handleWheel = (event: ReactWheelEvent<HTMLDivElement>) => {
      event.preventDefault();
      const zoomFactor = Math.exp(-event.deltaY * 0.0025);
      if (event.shiftKey) {
        setHorizontalGain((currentGain) =>
          clampNumber(
            currentGain * zoomFactor,
            EEG_HORIZONTAL_GAIN_MIN,
            EEG_HORIZONTAL_GAIN_MAX,
          ),
        );
        return;
      }
      setVerticalGain((currentGain) =>
        clampNumber(
          currentGain * zoomFactor,
          EEG_VERTICAL_GAIN_MIN,
          EEG_VERTICAL_GAIN_MAX,
        ),
      );
    };

    const getPinchDistance = () => {
      const [firstPointer, secondPointer] = [
        ...activePointersRef.current.values(),
      ];
      if (!firstPointer || !secondPointer) {
        return null;
      }
      return Math.hypot(
        secondPointer.x - firstPointer.x,
        secondPointer.y - firstPointer.y,
      );
    };

    const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId);
      activePointersRef.current.set(event.pointerId, {
        x: event.clientX,
        y: event.clientY,
      });
      const distance = getPinchDistance();
      if (distance) {
        pinchDistanceRef.current = distance;
        pinchGainRef.current = verticalGain;
      }
    };

    const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!activePointersRef.current.has(event.pointerId)) {
        return;
      }
      activePointersRef.current.set(event.pointerId, {
        x: event.clientX,
        y: event.clientY,
      });
      const distance = getPinchDistance();
      if (distance && pinchDistanceRef.current) {
        updateVerticalGain(
          pinchGainRef.current * (distance / pinchDistanceRef.current),
        );
      }
    };

    const handlePointerEnd = (event: ReactPointerEvent<HTMLDivElement>) => {
      activePointersRef.current.delete(event.pointerId);
      const distance = getPinchDistance();
      if (distance) {
        pinchDistanceRef.current = distance;
        pinchGainRef.current = verticalGain;
      } else {
        pinchDistanceRef.current = null;
      }
    };

    return (
      <div
        className="eeg-wave-preview relative flex h-full min-h-0 flex-col gap-2 touch-none"
        onDoubleClick={() => {
          setVerticalGain(1);
          setHorizontalGain(1);
        }}
        onPointerCancel={handlePointerEnd}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerEnd}
        onWheel={handleWheel}
      >
        <div
          className="eeg-wave-channels grid min-h-0 flex-1 gap-2"
          style={{
            gridTemplateRows: `repeat(${Math.max(1, visibleChannelNames.length)}, minmax(0, 1fr))`,
          }}
        >
          {visibleChannelNames.map((channelName, channelIndex) => (
            <div
              key={`channel_${channelIndex}`}
              className="h-full min-h-0 overflow-hidden rounded-[12px] bg-slate-950/20"
            >
              <EegWaveChannelPlot
                appendMeta={appendMeta}
                appendValues={appendChannelValues[channelIndex] || []}
                color={EEG_CHANNEL_COLORS[channelIndex] || "#60a5fa"}
                fullMeta={fullMeta}
                fullValues={fullChannelValues[channelIndex] || []}
                label={channelName}
                reset={reset}
                samplingRate={samplingRate}
                horizontalGain={horizontalGain}
                verticalGain={verticalGain}
              />
            </div>
          ))}
        </div>
        <div
          className="eeg-wave-controls order-first flex shrink-0 flex-wrap items-center justify-end gap-1 self-end rounded-lg border border-white/15 bg-slate-950/80 p-1 text-[10px] text-slate-200"
          onPointerDown={(event) => event.stopPropagation()}
          onDoubleClick={(event) => event.stopPropagation()}
        >
          <span className="ml-0.5 text-[9px] text-slate-400">纵向</span>
          <button
            type="button"
            aria-label="减小脑电波形纵向增益"
            className="rounded p-1 transition hover:bg-white/10"
            onClick={() =>
              setVerticalGain((currentGain) =>
                clampNumber(
                  currentGain / 1.35,
                  EEG_VERTICAL_GAIN_MIN,
                  EEG_VERTICAL_GAIN_MAX,
                ),
              )
            }
          >
            <Minus className="h-3 w-3" />
          </button>
          <span className="min-w-9 text-center font-medium tabular-nums">
            ×{verticalGain.toFixed(1)}
          </span>
          <button
            type="button"
            aria-label="增大脑电波形纵向增益"
            className="rounded p-1 transition hover:bg-white/10"
            onClick={() =>
              setVerticalGain((currentGain) =>
                clampNumber(
                  currentGain * 1.35,
                  EEG_VERTICAL_GAIN_MIN,
                  EEG_VERTICAL_GAIN_MAX,
                ),
              )
            }
          >
            <Plus className="h-3 w-3" />
          </button>
          <span className="mx-0.5 h-4 w-px bg-white/15" />
          <span className="text-[9px] text-slate-400">横向</span>
          <button
            type="button"
            aria-label="减小脑电波形横向增益"
            className="rounded p-1 transition hover:bg-white/10"
            onClick={() =>
              setHorizontalGain((currentGain) =>
                clampNumber(
                  currentGain / 1.35,
                  EEG_HORIZONTAL_GAIN_MIN,
                  EEG_HORIZONTAL_GAIN_MAX,
                ),
              )
            }
          >
            <Minus className="h-3 w-3" />
          </button>
          <span className="min-w-9 text-center font-medium tabular-nums">
            ×{horizontalGain.toFixed(1)}
          </span>
          <button
            type="button"
            aria-label="增大脑电波形横向增益"
            className="rounded p-1 transition hover:bg-white/10"
            onClick={() =>
              setHorizontalGain((currentGain) =>
                clampNumber(
                  currentGain * 1.35,
                  EEG_HORIZONTAL_GAIN_MIN,
                  EEG_HORIZONTAL_GAIN_MAX,
                ),
              )
            }
          >
            <Plus className="h-3 w-3" />
          </button>
          <button
            type="button"
            aria-label="恢复脑电自动尺度"
            className="ml-0.5 inline-flex items-center justify-center gap-1 rounded border border-white/10 px-1.5 py-1 text-[9px] transition hover:bg-white/10"
            onClick={() => {
              setVerticalGain(1);
              setHorizontalGain(1);
            }}
          >
            <RotateCcw className="h-2.5 w-2.5" /> 复位
          </button>
        </div>
        <div className="pointer-events-none shrink-0 text-right text-[10px] text-slate-400">
          最近{" "}
          {(EEG_WINDOW_SECONDS / horizontalGain).toFixed(
            horizontalGain === 1 ? 0 : 1,
          )}{" "}
          秒 · 滚轮纵向 / Shift + 滚轮横向 · 双击复位
        </div>
      </div>
    );
  },
  (previousProps, nextProps) => {
    if (previousProps.reset !== nextProps.reset) {
      return false;
    }
    if (previousProps.samplingRate !== nextProps.samplingRate) {
      return false;
    }
    if (
      !areChannelNamesEqual(previousProps.channelNames, nextProps.channelNames)
    ) {
      return false;
    }
    if (
      !areEegWaveSampleMetasEqual(
        extractEegWaveSampleMeta(previousProps.samples),
        extractEegWaveSampleMeta(nextProps.samples),
      )
    ) {
      return false;
    }
    return areEegWaveSampleMetasEqual(
      extractEegWaveSampleMeta(previousProps.appendSamples),
      extractEegWaveSampleMeta(nextProps.appendSamples),
    );
  },
);
