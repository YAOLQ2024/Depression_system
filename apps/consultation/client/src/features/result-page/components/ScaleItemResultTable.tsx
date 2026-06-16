import { cn } from "../../../lib/utils";
import type { ResultScaleItem } from "../types";
import { useResultTheme } from "../theme-context";
import { GlassCard } from "./GlassCard";

interface ScaleItemResultTableProps {
  items: ResultScaleItem[];
  className?: string;
  notice?: string | null;
}

export function ScaleItemResultTable({ items, className, notice }: ScaleItemResultTableProps) {
  const theme = useResultTheme();
  const isDark = theme === "dark";

  if (!items.length) {
    return null;
  }

  return (
    <div className={className}>
      <div className="mb-3 flex items-center gap-2 px-1">
        <div className="h-2 w-2 rounded-full bg-primary-500" />
        <h3 className={cn("text-lg font-bold", isDark ? "text-white" : "text-slate-900")}>详细作答</h3>
      </div>
      <GlassCard className="overflow-hidden">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr
              className={cn(
                "border-b",
                isDark ? "border-white/40 bg-white/20" : "border-slate-200 bg-slate-50/90",
              )}
            >
              <th className={cn("px-4 py-3 text-sm font-medium", isDark ? "text-white/80" : "text-slate-600")}>详细作答</th>
              <th className={cn("w-[220px] px-4 py-3 text-left text-sm font-medium", isDark ? "text-white/80" : "text-slate-600")}>用户选择</th>
            </tr>
          </thead>
          <tbody className={cn("divide-y", isDark ? "divide-white/30" : "divide-slate-200/80")}>
            {items.map((item, index) => (
              <tr
                key={`${item.no}-${index}`}
                className={cn(
                  "transition-colors",
                  isDark
                    ? "hover:bg-white/30"
                    : "hover:bg-violet-50/55",
                  index % 2 === 0
                    ? "bg-transparent"
                    : isDark
                      ? "bg-white/10"
                      : "bg-slate-50/60",
                )}
              >
                <td className={cn("px-4 py-3 text-sm", isDark ? "text-white" : "text-slate-700")}>
                  {item.no}. {item.label}
                </td>
                <td className={cn("px-4 py-3 text-sm", isDark ? "text-white" : "text-slate-700")}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "inline-flex rounded-full border px-3 py-1 text-sm font-medium",
                        isDark
                          ? "border-white/18 bg-white/[0.08] text-white"
                          : "border-violet-200 bg-violet-50 text-violet-600",
                      )}
                    >
                      {item.answerLabel || "未作答"}
                    </span>
                    {item.answerSource ? (
                      <span className={cn("text-xs", isDark ? "text-white/55" : "text-slate-400")}>
                        {item.answerSource === "voice"
                          ? "语音作答"
                          : item.answerSource === "click"
                            ? "点击作答"
                            : item.answerSource}
                      </span>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>
      {notice ? (
        <p className={cn("mt-3 px-1 text-sm leading-6", isDark ? "text-white/68" : "text-slate-500")}>{notice}</p>
      ) : null}
    </div>
  );
}
