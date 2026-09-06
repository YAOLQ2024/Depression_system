import { memo, useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode, type WheelEvent as ReactWheelEvent } from "react";
import { Activity, AudioLines, Minus, Plus, RefreshCw, RotateCcw, ScanFace, Sparkles } from "lucide-react";

import type { MediaDeviceStatusTone } from "../lib/mediaDeviceFeedback";
import { cn } from "../lib/utils";
import type {
  ConsultationMultimodalLive,
  ConsultationSession,
  ConsultationTurnMultimodalBundle,
  EegWaveSample,
  FacePoseMultimodalLive,
  MultimodalRankedLabel,
} from "../types";
import { CameraPreview } from "./CameraPreview";
import { EegEmotionImagePanel } from "./eeg/EegEmotionImagePanel";
import { EegWaveChannelPlot } from "./eeg/EegWaveChannelPlot";
import {
  EEG_HORIZONTAL_GAIN_MAX,
  EEG_HORIZONTAL_GAIN_MIN,
  EEG_WINDOW_SECONDS,
  EEG_VERTICAL_GAIN_MIN,
  EEG_VERTICAL_GAIN_MAX,
} from "./eeg/eegWaveWindow";
import { normalizeEegEmotionDistribution } from "./eeg/eegEmotionPresentation";

const EEG_CHANNEL_COLORS = ["#60a5fa", "#34d399", "#f59e0b"];

type EegWaveSampleMeta = {
  length: number;
  lastSeq: number | null;
  lastCapturedAtMs: number | null;
};

function buildPendingLive(): ConsultationMultimodalLive {
  return {
    speech: { status: "pending", top_3_labels: [] },
    text: { status: "pending", top_3_labels: [], negative_terms: [] },
    face: { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null },
    pose: { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null },
    eeg_live: {
      status: "pending",
      device_status: "pending",
      channel_names: ["T7", "T8", "Fpz"],
      sampling_rate: 500,
      latest_results: [],
    },
    eeg_waves: {
      status: "pending",
      channel_names: ["T7", "T8", "Fpz"],
      sampling_rate: 500,
      samples: [],
      append_samples: [],
      reset: false,
    },
    updated_at: null,
  };
}

function resolveLiveData(consultation: ConsultationSession): ConsultationMultimodalLive {
  const pending = buildPendingLive();
  const live: Partial<ConsultationMultimodalLive> = consultation.multimodal_live || {};

  return {
    ...pending,
    speech: {
      ...pending.speech,
      ...(live.speech || {}),
      top_3_labels: live.speech?.top_3_labels || pending.speech.top_3_labels,
    },
    text: {
      ...pending.text,
      ...(live.text || {}),
      top_3_labels: live.text?.top_3_labels || pending.text.top_3_labels,
      negative_terms: live.text?.negative_terms || pending.text.negative_terms,
    },
    face: {
      ...pending.face,
      ...(live.face || {}),
      top_3_labels: live.face?.top_3_labels || pending.face.top_3_labels,
      quality_flags: live.face?.quality_flags || pending.face.quality_flags,
    },
    pose: {
      ...pending.pose,
      ...(live.pose || {}),
      top_3_labels: live.pose?.top_3_labels || pending.pose.top_3_labels,
      quality_flags: live.pose?.quality_flags || pending.pose.quality_flags,
    },
    eeg_live: {
      ...pending.eeg_live,
      ...(live.eeg_live || {}),
      channel_names: live.eeg_live?.channel_names || pending.eeg_live.channel_names,
      latest_results: live.eeg_live?.latest_results || pending.eeg_live.latest_results,
    },
    eeg_waves: {
      ...pending.eeg_waves,
      ...(live.eeg_waves || {}),
      channel_names: live.eeg_waves?.channel_names || pending.eeg_waves.channel_names,
      samples: live.eeg_waves?.samples || pending.eeg_waves.samples,
      append_samples: live.eeg_waves?.append_samples || pending.eeg_waves.append_samples,
      reset: live.eeg_waves?.reset ?? pending.eeg_waves.reset,
    },
  };
}

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
  const lastSample = samples.length > 0 ? samples[samples.length - 1] : undefined;
  return {
    length: samples.length,
    lastSeq: typeof lastSample?.seq === "number" ? lastSample.seq : null,
    lastCapturedAtMs: parseCapturedAtTimestamp(lastSample?.captured_at),
  };
}

function areEegWaveSampleMetasEqual(left: EegWaveSampleMeta, right: EegWaveSampleMeta) {
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
    return typeof value === "number" && Number.isFinite(value) ? value : Number.NaN;
  });
}

type EegWavePreviewProps = {
  appendSamples: EegWaveSample[];
  channelNames: string[];
  reset: boolean;
  samples: EegWaveSample[];
  samplingRate: number;
};

const EegWavePreview = memo(function EegWavePreview({
  appendSamples,
  channelNames,
  reset,
  samples,
  samplingRate,
}: EegWavePreviewProps) {
  const [horizontalGain, setHorizontalGain] = useState(1);
  const [verticalGain, setVerticalGain] = useState(1);
  const activePointersRef = useRef(new Map<number, { x: number; y: number }>());
  const pinchDistanceRef = useRef<number | null>(null);
  const pinchGainRef = useRef(1);
  const visibleChannelNames = useMemo(() => channelNames.slice(0, 3), [channelNames]);
  const fullMeta = useMemo(() => extractEegWaveSampleMeta(samples), [samples]);
  const appendMeta = useMemo(() => extractEegWaveSampleMeta(appendSamples), [appendSamples]);
  const fullChannelValues = useMemo(
    () => visibleChannelNames.map((_, channelIndex) => extractChannelValues(samples, channelIndex)),
    [samples, visibleChannelNames],
  );
  const appendChannelValues = useMemo(
    () => visibleChannelNames.map((_, channelIndex) => extractChannelValues(appendSamples, channelIndex)),
    [appendSamples, visibleChannelNames],
  );

  const updateVerticalGain = (nextGain: number) => {
    setVerticalGain(clampNumber(nextGain, EEG_VERTICAL_GAIN_MIN, EEG_VERTICAL_GAIN_MAX));
  };

  const handleWheel = (event: ReactWheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    const zoomFactor = Math.exp(-event.deltaY * 0.0025);
    if (event.shiftKey) {
      setHorizontalGain((currentGain) => clampNumber(currentGain * zoomFactor, EEG_HORIZONTAL_GAIN_MIN, EEG_HORIZONTAL_GAIN_MAX));
      return;
    }
    setVerticalGain((currentGain) => clampNumber(currentGain * zoomFactor, EEG_VERTICAL_GAIN_MIN, EEG_VERTICAL_GAIN_MAX));
  };

  const getPinchDistance = () => {
    const [firstPointer, secondPointer] = [...activePointersRef.current.values()];
    if (!firstPointer || !secondPointer) {
      return null;
    }
    return Math.hypot(secondPointer.x - firstPointer.x, secondPointer.y - firstPointer.y);
  };

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    activePointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
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
    activePointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const distance = getPinchDistance();
    if (distance && pinchDistanceRef.current) {
      updateVerticalGain(pinchGainRef.current * (distance / pinchDistanceRef.current));
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
      className="relative grid h-full min-h-0 gap-1 pt-10 pb-6 touch-none"
      style={{ gridTemplateRows: `repeat(${Math.max(1, visibleChannelNames.length)}, minmax(0, 1fr))` }}
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
      <div
        className="absolute right-2 top-2 z-10 flex items-center gap-1 rounded-lg border border-white/15 bg-slate-950/80 p-1 text-[10px] text-slate-200 shadow-lg backdrop-blur-md"
        onPointerDown={(event) => event.stopPropagation()}
        onDoubleClick={(event) => event.stopPropagation()}
      >
        <span className="ml-0.5 text-[9px] text-slate-400">纵向</span>
        <button type="button" aria-label="减小脑电波形纵向增益" className="rounded p-1 transition hover:bg-white/10" onClick={() => setVerticalGain((currentGain) => clampNumber(currentGain / 1.35, EEG_VERTICAL_GAIN_MIN, EEG_VERTICAL_GAIN_MAX))}>
          <Minus className="h-3 w-3" />
        </button>
        <span className="min-w-9 text-center font-medium tabular-nums">×{verticalGain.toFixed(1)}</span>
        <button type="button" aria-label="增大脑电波形纵向增益" className="rounded p-1 transition hover:bg-white/10" onClick={() => setVerticalGain((currentGain) => clampNumber(currentGain * 1.35, EEG_VERTICAL_GAIN_MIN, EEG_VERTICAL_GAIN_MAX))}>
          <Plus className="h-3 w-3" />
        </button>
        <span className="mx-0.5 h-4 w-px bg-white/15" />
        <span className="text-[9px] text-slate-400">横向</span>
        <button type="button" aria-label="减小脑电波形横向增益" className="rounded p-1 transition hover:bg-white/10" onClick={() => setHorizontalGain((currentGain) => clampNumber(currentGain / 1.35, EEG_HORIZONTAL_GAIN_MIN, EEG_HORIZONTAL_GAIN_MAX))}>
          <Minus className="h-3 w-3" />
        </button>
        <span className="min-w-9 text-center font-medium tabular-nums">×{horizontalGain.toFixed(1)}</span>
        <button type="button" aria-label="增大脑电波形横向增益" className="rounded p-1 transition hover:bg-white/10" onClick={() => setHorizontalGain((currentGain) => clampNumber(currentGain * 1.35, EEG_HORIZONTAL_GAIN_MIN, EEG_HORIZONTAL_GAIN_MAX))}>
          <Plus className="h-3 w-3" />
        </button>
        <button type="button" aria-label="恢复脑电自动尺度" className="ml-0.5 inline-flex items-center justify-center gap-1 rounded border border-white/10 px-1.5 py-1 text-[9px] transition hover:bg-white/10" onClick={() => { setVerticalGain(1); setHorizontalGain(1); }}>
          <RotateCcw className="h-2.5 w-2.5" /> 复位
        </button>
      </div>
      <div className="pointer-events-none absolute bottom-1 right-2 z-10 rounded bg-slate-950/65 px-1.5 py-0.5 text-[9px] text-slate-400">
        最近 {(EEG_WINDOW_SECONDS / horizontalGain).toFixed(horizontalGain === 1 ? 0 : 1)} 秒 · 滚轮纵向 / Shift + 滚轮横向 · 双击复位
      </div>
    </div>
  );
}, (previousProps, nextProps) => {
  if (previousProps.reset !== nextProps.reset) {
    return false;
  }
  if (previousProps.samplingRate !== nextProps.samplingRate) {
    return false;
  }
  if (!areChannelNamesEqual(previousProps.channelNames, nextProps.channelNames)) {
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
});

function formatPercent(score?: number | null) {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return "0%";
  }
  const normalized = score <= 1 ? score * 100 : score;
  return `${Math.max(0, Math.min(100, Math.round(normalized)))}%`;
}

const EMOTION_LABELS_ZH: Record<string, string> = {
  ang: "愤怒",
  angry: "愤怒",
  calm: "平静",
  contempt: "轻蔑",
  disgust: "厌恶",
  fear: "恐惧",
  hap: "高兴",
  happy: "高兴",
  happiness: "高兴",
  label_0: "消极",
  label_1: "积极",
  negative: "消极",
  neg: "消极",
  neu: "中性",
  neutral: "中性",
  positive: "积极",
  pos: "积极",
  sad: "悲伤",
  sadness: "悲伤",
  surprise: "惊讶",
  surprised: "惊讶",
  unhappy: "不悦",
};

function localizeEmotionLabel(label: string) {
  const normalized = label.trim().toLowerCase();
  const localized = EMOTION_LABELS_ZH[normalized];
  if (localized) {
    return localized;
  }
  return /[a-z]/i.test(label) ? "情绪待识别" : label;
}

function getPrimaryLabel(label?: string | null, status?: string) {
  if (label) {
    return localizeEmotionLabel(label);
  }
  if (status === "failed") {
    return "识别失败";
  }
  return status === "ready" ? "已采样" : "等待中";
}

function getTopLabels(labels?: MultimodalRankedLabel[]) {
  return (labels || []).slice(0, 4);
}

function readBundleFaceSummary(bundle?: ConsultationTurnMultimodalBundle | null) {
  const face = (bundle?.face_features || {}) as Record<string, unknown>;
  const labelDistributionRaw = Array.isArray(face.label_distribution) ? face.label_distribution : [];
  const labelDistribution = labelDistributionRaw
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const record = item as Record<string, unknown>;
      const label = typeof record.label === "string" ? record.label : "";
      const ratio = typeof record.ratio === "number" ? record.ratio : 0;
      const count = typeof record.count === "number" ? record.count : 0;
      if (!label) {
        return null;
      }
      return { label, score: ratio, count };
    })
    .filter((item): item is { label: string; score: number; count: number } => Boolean(item));
  return {
    primary_label: typeof face.primary_label === "string" ? face.primary_label : null,
    primary_score: typeof face.primary_score === "number" ? face.primary_score : null,
    sample_count: typeof face.sample_count === "number" ? face.sample_count : null,
    valid_sample_count: typeof face.valid_sample_count === "number" ? face.valid_sample_count : null,
    label_distribution: labelDistribution,
  };
}

function readBundlePoseSummary(bundle?: ConsultationTurnMultimodalBundle | null) {
  const pose = (bundle?.pose_features || {}) as Record<string, unknown>;
  const labelDistributionRaw = Array.isArray(pose.label_distribution) ? pose.label_distribution : [];
  const labelDistribution = labelDistributionRaw
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const record = item as Record<string, unknown>;
      const label = typeof record.label === "string" ? record.label : "";
      const ratio = typeof record.ratio === "number" ? record.ratio : 0;
      const count = typeof record.count === "number" ? record.count : 0;
      if (!label) {
        return null;
      }
      return { label, score: ratio, count };
    })
    .filter((item): item is { label: string; score: number; count: number } => Boolean(item));
  return {
    primary_label: typeof pose.primary_label === "string" ? pose.primary_label : null,
    primary_score: typeof pose.primary_score === "number" ? pose.primary_score : null,
    sample_count: typeof pose.sample_count === "number" ? pose.sample_count : null,
    valid_sample_count: typeof pose.valid_sample_count === "number" ? pose.valid_sample_count : null,
    label_distribution: labelDistribution,
  };
}

function getFaceDetail(
  live: FacePoseMultimodalLive,
  bundleFace?: { sample_count: number | null; valid_sample_count: number | null } | null,
) {
  const parts: string[] = [];
  if (live.status === "failed" && live.error_message) {
    return live.error_message;
  }
  const sampleCount = bundleFace?.sample_count ?? live.sample_count;
  const validSampleCount = bundleFace?.valid_sample_count ?? live.valid_sample_count;
  if (typeof sampleCount === "number" && sampleCount > 0) {
    if (typeof validSampleCount === "number" && validSampleCount >= 0) {
      parts.push(`样本 ${validSampleCount}/${sampleCount}`);
    } else {
      parts.push(`样本 ${sampleCount}`);
    }
  }
  if (live.quality_flags?.no_face) {
    parts.push("未检测到人脸");
  }
  if (live.latest_capture_at) {
    parts.push("已更新");
  }
  return parts.join(" · ") || "等待采样";
}

function SectionCard({
  title,
  children,
  rightStatus = null,
  headerRight,
  className,
  contentClassName,
}: {
  title: string;
  children: ReactNode;
  rightStatus?: string | null;
  headerRight?: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  return (
    <div
      className={cn(
        "bg-slate-800/42 rounded-[20px] border border-white/10 p-[3px] flex flex-col relative overflow-hidden shadow-[0_4px_18px_rgba(0,0,0,0.18)]",
        className,
      )}
    >
      <div className={cn("flex justify-between gap-2 px-2 py-1", headerRight ? "items-start" : "items-center")}>
        <h3 className="min-w-0 text-[13px] font-semibold tracking-wide text-slate-100">{title}</h3>
        {headerRight ? (
          <div className="min-w-0 flex-1">{headerRight}</div>
        ) : rightStatus ? (
          <div className="flex items-center gap-1 text-[10px] text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-green-500"></span>
            {rightStatus}
          </div>
        ) : null}
      </div>
      <div className={cn("flex-1 min-h-0 px-2 pb-2", contentClassName)}>{children}</div>
    </div>
  );
}

function DistributionBar({ label, value }: { label: string; value: number }) {
  const percentage = Math.max(0, Math.min(100, Math.round(value <= 1 ? value * 100 : value)));
  return (
    <div className="flex items-center gap-2 text-[12px]">
      <span className="w-14 shrink-0 font-medium text-slate-200">{localizeEmotionLabel(label)}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-700/80">
        <div className="h-full rounded-full bg-blue-500" style={{ width: `${percentage}%` }} />
      </div>
      <span className="w-9 shrink-0 text-right font-medium text-slate-200">{percentage}%</span>
    </div>
  );
}

export function ConsultationStatusPanel({
  consultation,
  onRefresh,
  refreshing = false,
  isRecording = false,
  liveTransport = "HTTP",
  className,
  cameraStream = null,
  cameraReady = false,
  cameraError = null,
  cameraStatusTitle = "摄像头监测中",
  cameraStatusTone = "pending",
  microphoneStatusText = "麦克风待命",
}: {
  consultation: ConsultationSession;
  onRefresh: () => void;
  refreshing?: boolean;
  isRecording?: boolean;
  liveTransport?: "SSE" | "HTTP";
  className?: string;
  cameraStream?: MediaStream | null;
  cameraReady?: boolean;
  cameraError?: string | null;
  cameraStatusTitle?: string;
  cameraStatusTone?: MediaDeviceStatusTone;
  microphoneStatusText?: string;
}) {
  const snapshot = resolveLiveData(consultation);
  const currentTurnFaceBundle = readBundleFaceSummary(consultation.current_turn_bundle);
  const currentTurnPoseBundle = readBundlePoseSummary(consultation.current_turn_bundle);
  const liveFacePrimaryLabel = snapshot.face.primary_label || currentTurnFaceBundle.primary_label;
  const liveFacePrimaryScore = snapshot.face.primary_score ?? currentTurnFaceBundle.primary_score;
  const faceLabels =
    currentTurnFaceBundle.label_distribution.length > 0
      ? currentTurnFaceBundle.label_distribution
      : getTopLabels(snapshot.face.top_3_labels);
  const eegLatestResult = snapshot.eeg_live.latest_result;
  const eegDistribution = normalizeEegEmotionDistribution(eegLatestResult?.top_3_labels);
  const eegChannelNames = snapshot.eeg_waves.channel_names || snapshot.eeg_live.channel_names || ["T7", "T8", "Fpz"];
  const eegSamplingRate = snapshot.eeg_waves.sampling_rate || snapshot.eeg_live.sampling_rate || 500;
  const eegSamples = snapshot.eeg_waves.samples || [];
  const eegAppendSamples = snapshot.eeg_waves.append_samples || [];
  const eegWaveReset = Boolean(snapshot.eeg_waves.reset);
  const eegHasSamples = Boolean(eegSamples.length || eegAppendSamples.length);

  return (
    <div className={cn("w-full min-h-full font-sans text-slate-100 flex flex-col pt-0 bg-slate-900/40", className)}>
      <div className="flex items-center justify-between py-2 px-4 top-0 sticky bg-slate-900/82 backdrop-blur-md z-10 border-b border-indigo-500/20 shadow-md">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-300" />
          <h2 className="text-[18px] font-semibold tracking-wide text-white">多模态检测区</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex min-w-11 items-center justify-center rounded-[10px] border border-indigo-300/18 bg-indigo-500/18 px-2.5 py-1 text-[11px] font-semibold tracking-[0.08em] text-indigo-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
            {liveTransport}
          </span>
          <button
            onClick={onRefresh}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-200 transition hover:bg-white/10"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
            刷新
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-[3px] p-[3px]">
        <SectionCard
          title="表情检测"
          className="min-h-[290px]"
          rightStatus={null}
        >
          <div className="grid h-[246px] grid-cols-[1.2fr_0.8fr] gap-[3px]">
            <div className="h-full overflow-hidden rounded-[16px] border border-white/8">
              <CameraPreview
                className="h-full w-full !rounded-none !border-none !shadow-none"
                stream={cameraStream}
                cameraReady={cameraReady}
                audioActive={isRecording}
                title={cameraStatusTitle}
                headlineText={cameraStatusTitle}
                detailText={getFaceDetail(snapshot.face, currentTurnFaceBundle)}
                errorText={cameraError}
                statusTone={cameraStatusTone}
                audioStatusText={microphoneStatusText}
                showFooter={false}
              />
            </div>
            <div className="flex h-full min-h-0 flex-col rounded-[16px] bg-white/[0.03] px-3 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400">
                  <ScanFace className="h-6 w-6" />
                </div>
                <div>
                  <div className="text-[23px] font-bold leading-none text-emerald-400">
                    {getPrimaryLabel(liveFacePrimaryLabel, snapshot.face.status)}
                  </div>
                  <div className="mt-1 text-[14px] font-medium text-slate-200">
                    {formatPercent(liveFacePrimaryScore)} 置信度
                  </div>
                </div>
              </div>
              <div className="mt-3 flex min-h-0 flex-1 flex-col justify-between gap-1 overflow-hidden">
                {faceLabels.length > 0 ? (
                  faceLabels.map((item) => <DistributionBar key={item.label} label={item.label} value={item.score} />)
                ) : (
                  <div className="flex flex-1 items-center justify-center rounded-[14px] px-3 text-center text-[14px] leading-6 text-slate-400">
                    表情识别结果会在摄像头开启后显示。
                  </div>
                )}
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="脑电情绪监测"
          className="min-h-[370px]"
          contentClassName="p-0"
          headerRight={
            <div className="pt-0.5 text-right text-[13px] font-semibold tracking-[0.08em] text-slate-200">
              脑电情绪可视化
            </div>
          }
        >
          <div className="grid h-[336px] grid-cols-[1.78fr_1fr] gap-0">
            <div className="h-full min-w-0 overflow-hidden rounded-l-[16px] border border-dashed border-white/15">
              {eegHasSamples ? (
                <EegWavePreview
                  appendSamples={eegAppendSamples}
                  channelNames={eegChannelNames}
                  reset={eegWaveReset}
                  samples={eegSamples}
                  samplingRate={eegSamplingRate}
                />
              ) : (
                <div className="flex h-full items-center justify-center px-8 text-center text-[15px] leading-7 text-slate-300">
                  正在准备脑电信号，请佩戴好设备并按提示开始回答。
                </div>
              )}
            </div>
            <div className="h-full min-w-0 overflow-hidden rounded-r-[16px] border border-dashed border-white/15">
              <EegEmotionImagePanel
                distribution={eegDistribution}
                primaryLabel={eegLatestResult?.primary_label}
                primaryScore={eegLatestResult?.primary_score}
                deviceStatus={snapshot.eeg_live.device_status}
                errorMessage={snapshot.eeg_live.error_message}
              />
            </div>
          </div>
        </SectionCard>

        <div className="grid grid-cols-3 items-start gap-[3px]">
          <SectionCard
            title="姿态情绪检测"
            className="h-[196px]"
            rightStatus={null}
          >
            <div className="flex h-full flex-col items-center justify-center rounded-[16px] bg-white/[0.03] px-3 py-3 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-cyan-500/12 text-cyan-300">
                <Activity className="h-6 w-6" />
              </div>
              <div className="mt-3 min-w-0">
                <div className="text-[23px] font-semibold leading-none text-slate-100">
                  {getPrimaryLabel(currentTurnPoseBundle.primary_label || snapshot.pose.primary_label, snapshot.pose.status)}
                </div>
                <div className="mt-2 text-[15px] font-medium text-emerald-300">
                  {formatPercent(currentTurnPoseBundle.primary_score ?? snapshot.pose.primary_score)} 置信度
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            title="语音情绪检测"
            className="h-[196px]"
            rightStatus={null}
          >
            <div className="flex h-full flex-col items-center justify-center rounded-[16px] bg-white/[0.03] px-3 py-3 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/12 text-blue-300">
                <AudioLines className={cn("h-6 w-6", isRecording && "animate-pulse")} />
              </div>
              <div className="mt-3 min-w-0">
                <div className="text-[23px] font-semibold leading-none text-slate-100">
                  {getPrimaryLabel(snapshot.speech.primary_label, snapshot.speech.status)}
                </div>
                <div className="mt-2 text-[15px] font-medium text-emerald-300">
                  {formatPercent(snapshot.speech.primary_score)} 置信度
                </div>
              </div>
            </div>
          </SectionCard>
          <SectionCard title="文本情绪分析" className="h-[196px]" rightStatus={null}>
          <div className="flex h-full flex-col items-center justify-center rounded-[16px] bg-white/[0.03] px-3 py-3 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-500/12 text-indigo-300">
                <Sparkles className="h-6 w-6" />
              </div>
              <div className="mt-3 text-[23px] font-semibold leading-none text-slate-100">{getPrimaryLabel(snapshot.text.primary_label, snapshot.text.status)}</div>
              <div className="mt-2 text-[15px] font-medium text-emerald-300">{formatPercent(snapshot.text.primary_score)} 置信度</div>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
