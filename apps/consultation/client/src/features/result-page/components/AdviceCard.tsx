import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { cn } from "../../../lib/utils";
import { getToneClasses } from "../presentation";
import type { ResultCardTone } from "../types";
import { GlassCard } from "./GlassCard";
import { useResultTheme, themeClasses } from "../theme-context";

interface AdviceCardProps {
  icon: ReactNode;
  title: string;
  content: string;
  tone?: ResultCardTone;
  className?: string;
}

export function AdviceCard({ icon, title, content, tone = "blue", className }: AdviceCardProps) {
  const toneClasses = getToneClasses(tone);
  const theme = useResultTheme();
  const t = themeClasses;

  return (
    <GlassCard className={cn("flex items-start gap-3 p-4", className)}>
      <div className={cn("flex h-12 w-12 shrink-0 items-center justify-center rounded-full", toneClasses.iconBg, toneClasses.iconText)}>
        {icon}
      </div>
      <div className="mt-0.5 min-w-0 flex-1">
        <h4 className={cn("mb-1 text-base font-semibold", t.title[theme])}>{title}</h4>
        <p className={cn("text-sm leading-relaxed", t.body[theme])}>{content}</p>
      </div>
      <div className="shrink-0 pt-2 opacity-70">
        <ChevronRight className={cn("h-5 w-5", theme === "dark" ? "text-white/38" : "text-slate-300")} />
      </div>
    </GlassCard>
  );
}
