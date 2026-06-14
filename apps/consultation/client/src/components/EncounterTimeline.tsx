import { motion } from "motion/react";
import {
  ClipboardCheck,
  ClipboardList,
  FileText,
  PlayCircle,
  Stethoscope,
  Timer,
  UserCheck,
} from "lucide-react";
import { cn } from "../lib/utils";
import type { EncounterTimelineEvent } from "../services/api/contracts";

const EVENT_CONFIG: Record<string, { label: string; color: string; bg: string; ring: string; icon: React.ElementType }> = {
  encounter_created:      { label: "就诊创建",     color: "text-slate-500",  bg: "bg-slate-100",  ring: "ring-slate-200",  icon: FileText },
  encounter_started:      { label: "就诊开始",     color: "text-blue-600",   bg: "bg-blue-50",   ring: "ring-blue-200",   icon: PlayCircle },
  consultation_created:   { label: "问诊创建",     color: "text-indigo-600", bg: "bg-indigo-50", ring: "ring-indigo-200", icon: ClipboardList },
  consultation_started:   { label: "开始问诊",     color: "text-violet-600", bg: "bg-violet-50", ring: "ring-violet-200", icon: Stethoscope },
  consultation_completed: { label: "完成问诊",     color: "text-emerald-600",bg: "bg-emerald-50",ring: "ring-emerald-200",icon: ClipboardCheck },
  assessment_created:     { label: "量表创建",     color: "text-cyan-600",   bg: "bg-cyan-50",   ring: "ring-cyan-200",   icon: ClipboardList },
  assessment_started:     { label: "开始量表评估", color: "text-sky-600",    bg: "bg-sky-50",    ring: "ring-sky-200",    icon: Timer },
  assessment_completed:   { label: "完成量表评估", color: "text-teal-600",   bg: "bg-teal-50",   ring: "ring-teal-200",   icon: ClipboardCheck },
  encounter_completed:    { label: "就诊完成",     color: "text-emerald-600",bg: "bg-emerald-50",ring: "ring-emerald-200",icon: UserCheck },
};

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

type EncounterTimelineProps = {
  events: EncounterTimelineEvent[];
};

export function EncounterTimeline({ events }: EncounterTimelineProps) {
  if (!events.length) {
    return (
      <div className="py-8 text-center">
        <Timer className="mx-auto h-8 w-8 text-slate-300" />
        <p className="mt-2 text-sm text-slate-400">暂无时间线数据</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {events.map((event, index) => {
        const isLast = index === events.length - 1;
        const isFirst = index === 0;
        const config = EVENT_CONFIG[event.event] || {
          label: event.event,
          color: "text-slate-500",
          bg: "bg-slate-100",
          ring: "ring-slate-200",
          icon: FileText,
        };
        const Icon = config.icon;

        return (
          <motion.div
            key={`${event.event}-${index}`}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, delay: index * 0.08 }}
            className="relative flex gap-4"
          >
            {/* 连接线 */}
            {!isLast && (
              <div className="absolute left-[17px] top-[36px] h-[calc(100%-20px)] w-px bg-gradient-to-b from-slate-200 to-transparent" />
            )}

            {/* 图标节点 */}
            <div
              className={cn(
                "relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ring-1",
                isFirst ? config.bg + " " + config.ring : "bg-slate-50 ring-slate-200/60",
              )}
            >
              <Icon className={cn("h-4 w-4", isFirst ? config.color : "text-slate-400")} />
            </div>

            {/* 文字内容 */}
            <div className={cn("min-w-0 flex-1 pb-5", isLast && "pb-0")}>
              <div className="flex items-baseline gap-2">
                <span className={cn("text-sm font-medium", isFirst ? "text-slate-900" : "text-slate-600")}>
                  {config.label}
                </span>
                <span className="text-xs text-slate-400">{formatDate(event.at)}</span>
              </div>
              <p className="mt-0.5 text-xs text-slate-400">{formatTime(event.at)}</p>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
