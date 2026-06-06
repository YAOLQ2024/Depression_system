import { cn } from "../../../lib/utils";
import type { ResultScaleItem } from "../types";
import { GlassCard } from "./GlassCard";

interface ScaleItemResultTableProps {
  items: ResultScaleItem[];
  className?: string;
  notice?: string | null;
}

export function ScaleItemResultTable({ items, className, notice }: ScaleItemResultTableProps) {
  if (!items.length) {
    return null;
  }

  return (
    <div className={className}>
      <div className="mb-3 flex items-center gap-2 px-1">
        <div className="h-2 w-2 rounded-full bg-primary-500" />
        <h3 className="text-lg font-bold text-white">详细作答</h3>
      </div>
      <GlassCard className="overflow-hidden">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-white/40 bg-white/20">
              <th className="px-4 py-3 text-sm font-medium text-white/80">详细作答</th>
              <th className="w-[220px] px-4 py-3 text-left text-sm font-medium text-white/80">用户选择</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/30">
            {items.map((item, index) => (
              <tr
                key={`${item.no}-${index}`}
                className={cn(
                  "transition-colors hover:bg-white/30",
                  index % 2 === 0 ? "bg-transparent" : "bg-white/10",
                )}
              >
                <td className="px-4 py-3 text-sm text-white">
                  {item.no}. {item.label}
                </td>
                <td className="px-4 py-3 text-sm text-white">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex rounded-full border border-white/18 bg-white/[0.08] px-3 py-1 text-sm font-medium text-white">
                      {item.answerLabel || "未作答"}
                    </span>
                    {item.answerSource ? (
                      <span className="text-xs text-white/55">
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
        <p className="mt-3 px-1 text-sm leading-6 text-white/68">{notice}</p>
      ) : null}
    </div>
  );
}
