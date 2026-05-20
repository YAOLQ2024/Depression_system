import type { ReactNode } from "react";
import { Activity, AudioLines, BrainCircuit, RefreshCw, ScanFace, Sparkles } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";

import type { MediaDeviceStatusTone } from "../lib/mediaDeviceFeedback";
import { cn } from "../lib/utils";
import type {
  ConsultationMultimodalLive,
  ConsultationSession,
  FacePoseMultimodalLive,
  MultimodalRankedLabel,
  SpeechMultimodalLive,
  TextMultimodalLive,
} from "../types";
import { CameraPreview } from "./CameraPreview";

function buildEegSeries(stageOrder: number) {
  return Array.from({ length: 30 }, (_, idx) => {
    const base = idx / 4;
    const offset = stageOrder * 0.35;

    return {
      idx,
      alpha: Number((Math.sin(base + offset) * 0.35 + 0.45).toFixed(3)),
      beta: Number((Math.cos(base * 1.25 + offset) * 0.28 + 0.52).toFixed(3)),
      theta: Number((Math.sin(base * 0.75 + 1.8 + offset) * 0.22 + 0.38).toFixed(3)),
    };
  });
}

function buildPendingLive(): ConsultationMultimodalLive {
  return {
    speech: { status: "pending", top_3_labels: [] },
    text: { status: "pending", top_3_labels: [], negative_terms: [] },
    face: { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null },
    pose: { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null },
    updated_at: null,
  };
}

function resolveLiveData(consultation: ConsultationSession): ConsultationMultimodalLive {
  const pending = buildPendingLive();
  const live: Partial<ConsultationMultimodalLive> = consultation.multimodal_live || {};

  return {
    ...pending,
    ...live,
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
  };
}

function formatPercent(score?: number | null) {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return "0%";
  }
  const normalized = score <= 1 ? score * 100 : score;
  return `${Math.max(0, Math.min(100, Math.round(normalized)))}%`;
}

function getPrimaryLabel(label?: string | null, status?: string) {
  if (label) {
    return label;
  }
  return status === "ready" ? "已采样" : "等待中";
}

function getTopLabels(labels?: MultimodalRankedLabel[]) {
  return (labels || []).slice(0, 4);
}

function getFaceDetail(live: FacePoseMultimodalLive) {
  const parts: string[] = [];
  if (typeof live.sample_count === "number" && live.sample_count > 0) {
    parts.push(`样本 ${live.sample_count}`);
  }
  if (live.latest_capture_at) {
    parts.push("已更新");
  }
  return parts.join(" · ") || "等待采样";
}

function getPoseDetail(live: FacePoseMultimodalLive) {
  const flags = live.quality_flags || {};
  const ratios = Object.entries(flags)
    .filter(([, value]) => typeof value === "number" && (value as number) > 0)
    .slice(0, 2)
    .map(([key, value]) => `${key}:${formatPercent(value as number)}`);
  return ratios.join(" · ") || "等待采样";
}

function getVoiceDetail(live: SpeechMultimodalLive, isRecording: boolean) {
  if (isRecording) {
    return "录音与识别进行中";
  }
  if (live.captured_at) {
    return "本轮语音已入库";
  }
  return "等待语音提交";
}

function getTextBody(live: TextMultimodalLive, transcriptPending: boolean) {
  if (live.transcript_text?.trim()) {
    return live.transcript_text.trim();
  }
  if (transcriptPending) {
    return "Dolphin 识别中，等待本轮最终转写文本。";
  }
  return "等待患者语音转写文本。";
}

function SectionCard({
  title,
  children,
  rightStatus = "实时",
  className,
}: {
  title: string;
  children: ReactNode;
  rightStatus?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "bg-slate-800/42 rounded-[20px] border border-white/10 p-[3px] flex flex-col relative overflow-hidden shadow-[0_4px_18px_rgba(0,0,0,0.18)]",
        className,
      )}
    >
      <div className="flex items-center justify-between px-2 py-1.5">
        <h3 className="text-[13px] font-semibold text-slate-100 tracking-wide">{title}</h3>
        <div className="flex items-center gap-1 text-[10px] text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
          {rightStatus}
        </div>
      </div>
      <div className="flex-1 px-2 pb-2">{children}</div>
    </div>
  );
}

function DistributionBar({ label, value }: { label: string; value: number }) {
  const percentage = Math.max(0, Math.min(100, Math.round(value <= 1 ? value * 100 : value)));
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <span className="w-14 shrink-0 text-slate-400">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-700/80">
        <div className="h-full rounded-full bg-blue-500" style={{ width: `${percentage}%` }} />
      </div>
      <span className="w-8 shrink-0 text-right text-slate-400">{percentage}%</span>
    </div>
  );
}

function WaveBars({ active }: { active: boolean }) {
  const barHeights = active ? [22, 34, 18, 42, 24, 36, 14, 40, 20, 30, 16, 28] : [8, 12, 10, 14, 9, 13, 7, 12, 8, 11, 7, 9];

  return (
    <div className="flex h-12 items-end justify-center gap-[3px]">
      {barHeights.map((height, index) => (
        <span
          key={`${height}-${index}`}
          className={cn("w-[3px] rounded-full bg-blue-500/90 transition-all duration-300", active && "animate-pulse")}
          style={{
            height,
            animationDelay: `${index * 90}ms`,
            animationDuration: active ? "900ms" : "1400ms",
          }}
        />
      ))}
    </div>
  );
}

function NegativeWordBadge({ word }: { word: string }) {
  return (
    <span className="rounded-full border border-rose-300/20 bg-rose-500/10 px-2 py-0.5 text-[10px] text-rose-200">
      {word}
    </span>
  );
}

export function ConsultationStatusPanel({
  consultation,
  onRefresh,
  refreshing = false,
  isRecording = false,
  className,
  cameraStream = null,
  cameraReady = false,
  cameraError = null,
  cameraStatusTitle = "摄像头监测中",
  cameraStatusTone = "pending",
  microphoneStatusText = "麦克风待命",
  transcriptPending = false,
}: {
  consultation: ConsultationSession;
  onRefresh: () => void;
  refreshing?: boolean;
  isRecording?: boolean;
  className?: string;
  cameraStream?: MediaStream | null;
  cameraReady?: boolean;
  cameraError?: string | null;
  cameraStatusTitle?: string;
  cameraStatusTone?: MediaDeviceStatusTone;
  microphoneStatusText?: string;
  transcriptPending?: boolean;
}) {
  const snapshot = resolveLiveData(consultation);
  const stageOrder = consultation.current_stage?.stage_order ?? consultation.current_question_item?.stage_order ?? 1;
  const eegSeries = buildEegSeries(stageOrder);
  const faceLabels = getTopLabels(snapshot.face.top_3_labels);
  const textWords = snapshot.text.negative_terms || [];

  return (
    <div className={cn("w-full h-full min-h-0 font-sans text-slate-100 flex flex-col pt-0 bg-slate-900/40", className)}>
      <div className="flex items-center justify-between py-3 px-4 top-0 sticky bg-slate-900/82 backdrop-blur-md z-10 border-b border-indigo-500/20 shadow-md">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-indigo-300" />
          <h2 className="text-[20px] font-semibold tracking-wide text-white">多模态检测区</h2>
        </div>
        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-200 transition hover:bg-white/10"
        >
          <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
          刷新
        </button>
      </div>

      <div className="flex-1 flex flex-col gap-[3px] p-[3px]">
        <SectionCard title="表情检测" rightStatus={snapshot.face.status === "ready" ? "ready" : "pending"}>
          <div className="grid grid-cols-[1.2fr_0.8fr] gap-[3px] h-[180px]">
            <div className="h-full overflow-hidden rounded-[16px] border border-white/8">
              <CameraPreview
                className="h-full w-full !rounded-none !border-none !shadow-none"
                stream={cameraStream}
                cameraReady={cameraReady}
                audioActive={isRecording}
                title={cameraStatusTitle}
                headlineText={cameraStatusTitle}
                detailText={getFaceDetail(snapshot.face)}
                errorText={cameraError}
                statusTone={cameraStatusTone}
                audioStatusText={microphoneStatusText}
              />
            </div>
            <div className="flex h-full flex-col justify-between rounded-[16px] bg-white/[0.03] px-2 py-2">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400">
                  <ScanFace className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[19px] font-bold leading-none text-emerald-400">
                    {getPrimaryLabel(snapshot.face.primary_label, snapshot.face.status)}
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-300">{formatPercent(snapshot.face.primary_score)} 置信度</div>
                </div>
              </div>
              <div className="mt-2 space-y-1.5">
                {faceLabels.length > 0 ? (
                  faceLabels.map((item) => <DistributionBar key={item.label} label={item.label} value={item.score} />)
                ) : (
                  <div className="rounded-[14px] border border-dashed border-white/10 px-3 py-4 text-center text-[11px] text-slate-400">
                    摄像头已开启后会持续上传表情帧并在这里显示结果。
                  </div>
                )}
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="脑电趋势感知">
          <div className="grid grid-cols-[2fr_1fr] gap-[3px] h-[180px]">
            <div className="min-w-0 rounded-[16px] bg-white/[0.03] px-1 py-1">
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
                <LineChart data={eegSeries} margin={{ top: 10, right: 8, bottom: 4, left: -24 }}>
                  <YAxis hide domain={[0, 1]} />
                  <Line type="monotone" dataKey="alpha" stroke="#60a5fa" strokeWidth={1.7} dot={false} />
                  <Line type="monotone" dataKey="beta" stroke="#34d399" strokeWidth={1.6} dot={false} />
                  <Line type="monotone" dataKey="theta" stroke="#c084fc" strokeWidth={1.6} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="rounded-[16px] border border-dashed border-white/10 bg-[radial-gradient(circle_at_center,rgba(96,165,250,0.18),transparent_58%)] px-2 py-2 flex items-center justify-center">
              <div className="text-center">
                <BrainCircuit className="mx-auto h-8 w-8 text-indigo-200/80" />
                <p className="mt-2 text-[11px] text-slate-300">脑电地形图</p>
                <p className="mt-1 text-[10px] text-slate-500">当前前端未接 EEG</p>
              </div>
            </div>
          </div>
        </SectionCard>

        <div className="grid grid-cols-2 gap-[3px]">
          <SectionCard title="姿态情绪检测" rightStatus={snapshot.pose.status === "ready" ? "ready" : "pending"}>
            <div className="flex h-full items-center gap-3 rounded-[16px] bg-white/[0.03] px-2 py-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-cyan-500/12 text-cyan-300">
                <Activity className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="text-[18px] font-semibold text-slate-100">{getPrimaryLabel(snapshot.pose.primary_label, snapshot.pose.status)}</div>
                <div className="mt-1 text-[12px] text-emerald-300">{formatPercent(snapshot.pose.primary_score)} 置信度</div>
                <div className="mt-1 text-[11px] text-slate-400">{getPoseDetail(snapshot.pose)}</div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="语音情绪检测" rightStatus={snapshot.speech.status === "ready" ? "ready" : "pending"}>
            <div className="flex h-full items-center gap-3 rounded-[16px] bg-white/[0.03] px-2 py-2">
              <div className="flex-1">
                <WaveBars active={isRecording} />
              </div>
              <div className="min-w-[100px] text-right">
                <div className="flex items-center justify-end gap-1 text-blue-300">
                  <AudioLines className="h-4 w-4" />
                  <span className="text-[11px]">语音</span>
                </div>
                <div className="mt-1 text-[16px] font-semibold text-slate-100">
                  {getPrimaryLabel(snapshot.speech.primary_label, snapshot.speech.status)}
                </div>
                <div className="mt-1 text-[11px] text-slate-400">{getVoiceDetail(snapshot.speech, isRecording)}</div>
              </div>
            </div>
          </SectionCard>
        </div>

        <SectionCard title="文本情绪分析" className="flex-1 min-h-[140px]" rightStatus={snapshot.text.status === "ready" ? "ready" : "pending"}>
          <div className="flex h-full flex-col rounded-[16px] bg-white/[0.03] px-2 py-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-500/12 text-indigo-300">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[16px] font-semibold text-slate-100">{getPrimaryLabel(snapshot.text.primary_label, snapshot.text.status)}</div>
                  <div className="text-[12px] text-emerald-300">{formatPercent(snapshot.text.primary_score)} 置信度</div>
                </div>
              </div>
              <div className="flex flex-wrap justify-end gap-1.5 max-w-[46%]">
                {textWords.length > 0 ? textWords.map((word) => <NegativeWordBadge key={word} word={word} />) : null}
              </div>
            </div>
            <div className="mt-2 flex-1 rounded-[14px] border border-white/8 bg-slate-950/20 px-2 py-2 text-[12px] leading-6 text-slate-200">
              {getTextBody(snapshot.text, transcriptPending)}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
