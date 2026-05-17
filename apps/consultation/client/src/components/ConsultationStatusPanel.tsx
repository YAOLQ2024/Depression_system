import type { ReactNode } from "react";
import { Activity, AudioLines, BrainCircuit, RefreshCw, ScanFace, Sparkles } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";

import { cn } from "../lib/utils";
import type { ConsultationSession } from "../types";
import { CameraPreview } from "./CameraPreview";

type MetricDistribution = {
  label: string;
  value: number;
};

type MonitorSnapshot = {
  facePrimaryLabel: string;
  facePrimaryConfidence: number;
  faceDistribution: MetricDistribution[];
  poseLabel: string;
  poseConfidence: number;
  voiceLabel: string;
  voiceConfidence: number;
  textLabel: string;
  textConfidence: number;
  transcriptText: string;
  negativeWords: string[];
  eegSeries: Array<{ idx: number; alpha: number; beta: number; theta: number }>;
};

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

function buildMonitorSnapshot(consultation: ConsultationSession, isRecording: boolean): MonitorSnapshot {
  const stageOrder = consultation.current_stage?.stage_order ?? consultation.current_question_item?.stage_order ?? 1;

  const stagePresets: Record<number, Omit<MonitorSnapshot, "eegSeries">> = {
    1: {
      facePrimaryLabel: "平静",
      facePrimaryConfidence: 76,
      faceDistribution: [
        { label: "中性", value: 15 },
        { label: "轻度悲伤", value: 7 },
        { label: "焦虑", value: 2 },
        { label: "其他", value: 0 },
      ],
      poseLabel: "坐姿稳定",
      poseConfidence: 92,
      voiceLabel: isRecording ? "语音平稳" : "等待输入",
      voiceConfidence: isRecording ? 88 : 0,
      textLabel: "待输入",
      textConfidence: 0,
      transcriptText: isRecording ? "语音输入中..." : "当前暂无患者语音转写文本。",
      negativeWords: [],
    },
    2: {
      facePrimaryLabel: "专注",
      facePrimaryConfidence: 73,
      faceDistribution: [
        { label: "平静", value: 18 },
        { label: "紧张", value: 9 },
        { label: "轻度悲伤", value: 6 },
        { label: "其他", value: 4 },
      ],
      poseLabel: "轻微前倾",
      poseConfidence: 81,
      voiceLabel: isRecording ? "语速平稳" : "等待输入",
      voiceConfidence: isRecording ? 84 : 0,
      textLabel: "待输入",
      textConfidence: 0,
      transcriptText: isRecording ? "语音输入中..." : "等待患者开始本轮语音回答。",
      negativeWords: ["暂无"],
    },
    3: {
      facePrimaryLabel: "低落",
      facePrimaryConfidence: 61,
      faceDistribution: [
        { label: "平静", value: 14 },
        { label: "悲伤", value: 19 },
        { label: "疲惫", value: 11 },
        { label: "其他", value: 6 },
      ],
      poseLabel: "动作减缓",
      poseConfidence: 69,
      voiceLabel: isRecording ? "语音偏弱" : "等待输入",
      voiceConfidence: isRecording ? 67 : 0,
      textLabel: "待输入",
      textConfidence: 0,
      transcriptText: isRecording ? "语音输入中..." : "等待患者开始本轮语音回答。",
      negativeWords: ["暂无"],
    },
    4: {
      facePrimaryLabel: "警觉",
      facePrimaryConfidence: 68,
      faceDistribution: [
        { label: "平静", value: 12 },
        { label: "焦虑", value: 18 },
        { label: "担忧", value: 10 },
        { label: "其他", value: 5 },
      ],
      poseLabel: "姿态紧绷",
      poseConfidence: 74,
      voiceLabel: isRecording ? "波动明显" : "等待输入",
      voiceConfidence: isRecording ? 71 : 0,
      textLabel: "待输入",
      textConfidence: 0,
      transcriptText: isRecording ? "语音输入中..." : "等待患者开始本轮语音回答。",
      negativeWords: ["暂无"],
    },
  };

  const preset = stagePresets[stageOrder] || stagePresets[1];
  return {
    ...preset,
    eegSeries: buildEegSeries(stageOrder),
  };
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
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <span className="w-14 shrink-0 text-slate-400">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-700/80">
        <div className="h-full rounded-full bg-blue-500" style={{ width: `${value}%` }} />
      </div>
      <span className="w-8 shrink-0 text-right text-slate-400">{value}%</span>
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
          className={cn(
            "w-[3px] rounded-full bg-blue-500/90 transition-all duration-300",
            active && "animate-pulse",
          )}
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
  const isEmpty = word === "暂无";
  return (
    <span
      className={cn(
        "rounded-full border px-2 py-0.5 text-[10px]",
        isEmpty ? "border-white/12 text-slate-400" : "border-rose-300/20 bg-rose-500/10 text-rose-200",
      )}
    >
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
}: {
  consultation: ConsultationSession;
  onRefresh: () => void;
  refreshing?: boolean;
  isRecording?: boolean;
  className?: string;
}) {
  const snapshot = buildMonitorSnapshot(consultation, isRecording);

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
        <SectionCard title="表情检测">
          <div className="grid grid-cols-[1.2fr_0.8fr] gap-[3px] h-[180px]">
            <div className="h-full overflow-hidden rounded-[16px] border border-white/8">
              <CameraPreview className="h-full w-full !rounded-none !border-none !shadow-none" />
            </div>
            <div className="flex h-full flex-col justify-between rounded-[16px] bg-white/[0.03] px-2 py-2">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400">
                  <ScanFace className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[19px] font-bold leading-none text-emerald-400">{snapshot.facePrimaryLabel}</div>
                  <div className="mt-0.5 text-[11px] text-slate-300">{snapshot.facePrimaryConfidence}% 置信度</div>
                </div>
              </div>
              <div className="mt-2 space-y-1.5">
                {snapshot.faceDistribution.map((item) => (
                  <DistributionBar key={item.label} label={item.label} value={item.value} />
                ))}
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="脑电趋势感知">
          <div className="grid grid-cols-[2fr_1fr] gap-[3px] h-[180px]">
            <div className="rounded-[16px] bg-white/[0.03] px-1 py-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={snapshot.eegSeries} margin={{ top: 10, right: 8, bottom: 4, left: -24 }}>
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
                <p className="mt-1 text-[10px] text-slate-500">占位区</p>
              </div>
            </div>
          </div>
        </SectionCard>

        <div className="grid grid-cols-2 gap-[3px]">
          <SectionCard title="姿态情绪检测">
            <div className="flex h-full items-center gap-3 rounded-[16px] bg-white/[0.03] px-2 py-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-cyan-500/12 text-cyan-300">
                <Activity className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <div className="text-[18px] font-semibold text-slate-100">{snapshot.poseLabel}</div>
                <div className="mt-1 text-[12px] text-emerald-300">{snapshot.poseConfidence}% 置信度</div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="语音情绪检测">
            <div className="flex h-full items-center gap-3 rounded-[16px] bg-white/[0.03] px-2 py-2">
              <div className="flex-1">
                <WaveBars active={isRecording} />
              </div>
              <div className="min-w-[84px] text-right">
                <div className="flex items-center justify-end gap-1 text-blue-300">
                  <AudioLines className="h-4 w-4" />
                  <span className="text-[11px]">语音</span>
                </div>
                <div className="mt-1 text-[16px] font-semibold text-slate-100">{snapshot.voiceLabel}</div>
                <div className="mt-1 text-[12px] text-emerald-300">{snapshot.voiceConfidence}% 置信度</div>
              </div>
            </div>
          </SectionCard>
        </div>

        <SectionCard title="文本情绪分析" className="flex-1 min-h-[140px]">
          <div className="flex h-full flex-col rounded-[16px] bg-white/[0.03] px-2 py-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-500/12 text-indigo-300">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-[16px] font-semibold text-slate-100">{snapshot.textLabel}</div>
                  <div className="text-[12px] text-emerald-300">{snapshot.textConfidence}% 置信度</div>
                </div>
              </div>
              <div className="flex flex-wrap justify-end gap-1.5 max-w-[46%]">
                {snapshot.negativeWords.map((word) => (
                  <NegativeWordBadge key={word} word={word} />
                ))}
              </div>
            </div>
            <div className="mt-2 flex-1 rounded-[14px] border border-white/8 bg-slate-950/20 px-2 py-2 text-[12px] leading-6 text-slate-200">
              {snapshot.transcriptText}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
