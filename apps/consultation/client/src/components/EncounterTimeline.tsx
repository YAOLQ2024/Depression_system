import { cn } from "../lib/utils";
import type { EncounterTimelineEvent } from "../services/api/contracts";

const EVENT_LABELS: Record<string, string> = {
  encounter_created: "就诊创建",
  encounter_started: "就诊开始",
  consultation_created: "问诊创建",
  consultation_started: "开始问诊",
  consultation_completed: "完成问诊",
  assessment_created: "量表创建",
  assessment_started: "开始量表评估",
  assessment_completed: "完成量表评估",
  encounter_completed: "就诊完成",
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
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

type EncounterTimelineProps = {
  events: EncounterTimelineEvent[];
};

export function EncounterTimeline({ events }: EncounterTimelineProps) {
  if (!events.length) {
    return <p className="text-sm text-slate-500">暂无时间线数据</p>;
  }

  return (
    <div className="space-y-0">
      {events.map((event, index) => {
        const isLast = index === events.length - 1;
        const label = EVENT_LABELS[event.event] || event.event;

        return (
          <div key={`${event.event}-${index}`} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "w-2.5 h-2.5 rounded-full mt-1.5 shrink-0",
                  index === 0 ? "bg-indigo-400" : isLast ? "bg-emerald-400" : "bg-slate-500",
                )}
              />
              {!isLast && <div className="w-px flex-1 bg-slate-700 min-h-[20px]" />}
            </div>
            <div className={cn("pb-4", isLast && "pb-0")}>
              <p className="text-sm text-slate-200">{label}</p>
              <p className="text-xs text-slate-500">
                {formatDate(event.at)} {formatTime(event.at)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
