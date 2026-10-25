import { useEffect, useRef, useState, type ReactNode } from "react";
import { Activity, AudioLines, RefreshCw, ScanFace, Sparkles } from "lucide-react";

import type { MediaDeviceStatusTone } from "../lib/mediaDeviceFeedback";
import { cn } from "../lib/utils";
import type {
  ConsultationMultimodalLive,
  ConsultationSession,
  ConsultationTurnMultimodalBundle,
  FacePoseMultimodalLive,
  MultimodalRankedLabel,
} from "../types";
import { CameraPreview } from "./CameraPreview";
import { EegMirrorPanel } from "./eeg/EegMirrorPanel";

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
    eeg_explanation_status: live.eeg_explanation_status,
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
  other: "其他",
  positive: "积极",
  pos: "积极",
  sad: "悲伤",
  sadness: "悲伤",
  surprise: "惊讶",
  surprised: "惊讶",
  unhappy: "不悦",
  unknown: "未知",
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
        "consultation-dashboard-card bg-slate-800/42 rounded-[20px] border border-white/10 p-[3px] flex flex-col relative overflow-hidden shadow-[0_4px_18px_rgba(0,0,0,0.18)]",
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
  onClose,
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
  onClose?: () => void;
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
  const displayedFaceBundleRef = useRef<{
    turnId: string;
    summary: ReturnType<typeof readBundleFaceSummary>;
  } | null>(null);
  const currentTurnId = consultation.current_turn_bundle?.turn_id || null;
  const currentFaceSampleCount =
    currentTurnFaceBundle.valid_sample_count ?? currentTurnFaceBundle.sample_count ?? 0;
  let displayedFaceBundle = currentTurnFaceBundle;
  let isUsingPreviousFaceBundle = false;

  if (currentTurnId) {
    const previous = displayedFaceBundleRef.current;
    if (!previous || previous.turnId === currentTurnId || currentFaceSampleCount >= 3) {
      displayedFaceBundleRef.current = {
        turnId: currentTurnId,
        summary: currentTurnFaceBundle,
      };
    } else {
      // Keep the completed previous-turn distribution visible until the new
      // turn has enough frames to form a meaningful distribution.
      displayedFaceBundle = previous.summary;
      isUsingPreviousFaceBundle = true;
    }
  } else if (displayedFaceBundleRef.current) {
    displayedFaceBundle = displayedFaceBundleRef.current.summary;
    isUsingPreviousFaceBundle = true;
  }

  const liveFacePrimaryLabel = isUsingPreviousFaceBundle
    ? displayedFaceBundle.primary_label
    : snapshot.face.primary_label || displayedFaceBundle.primary_label;
  const faceLabels =
    displayedFaceBundle.label_distribution.length > 0
      ? displayedFaceBundle.label_distribution
      : getTopLabels(snapshot.face.top_3_labels);

  return (
    <div className={cn("consultation-dashboard w-full min-h-full font-sans text-slate-100 flex flex-col pt-0 bg-slate-900/40", className)}>
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
          {onClose ? <button type="button" onClick={onClose} className="consultation-portrait-close" aria-label="收起多模态看板">收起看板 ↓</button> : null}
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
                detailText={getFaceDetail(snapshot.face, displayedFaceBundle)}
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

        <EegMirrorPanel sessionId={consultation.multimodal_session_id} live={snapshot.eeg_live} waves={snapshot.eeg_waves} explanationUpdate={snapshot.eeg_explanation_status ? `${snapshot.eeg_explanation_status.explanation_id}:${snapshot.eeg_explanation_status.status}` : undefined} />

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
