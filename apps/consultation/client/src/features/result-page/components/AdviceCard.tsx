import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "../../../lib/utils";
import { getToneClasses } from "../presentation";
import type { ResultCardTone } from "../types";
import { GlassCard } from "./GlassCard";

interface AdviceCardProps {
  icon: ReactNode;
  title: string;
  content: string;
  tone?: ResultCardTone;
  className?: string;
}

export function AdviceCard({ icon, title, content, tone = "blue", className }: AdviceCardProps) {
  const toneClasses = getToneClasses(tone);

  return (
    <GlassCard className={cn("flex items-start gap-3 p-4", className)}>
      <div
        className={cn(
          "flex h-12 w-12 shrink-0 items-center justify-center rounded-full",
          toneClasses.iconBg,
          toneClasses.iconText,
        )}
      >
        {icon}
      </div>
      <div className="mt-0.5 min-w-0 flex-1">
        <h4 className="mb-1 text-base font-semibold text-white">{title}</h4>
        <p className="text-sm leading-relaxed text-white/72">{content}</p>
      </div>
      <div className="shrink-0 pt-2 opacity-70">
        <ChevronRight className="h-5 w-5 text-white/38" />
      </div>
    </GlassCard>
  );
}
