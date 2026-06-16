import { cn } from "../../../lib/utils";
import { getSeverityBadgeClasses } from "../presentation";

interface SeverityBadgeProps {
  level?: string | null;
  className?: string;
}

export function SeverityBadge({ level, className }: SeverityBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full shrink-0 items-center justify-center rounded-full border px-3 py-1 text-sm font-medium leading-none whitespace-nowrap backdrop-blur-md",
        getSeverityBadgeClasses(level),
        className,
      )}
    >
      {level || "待评估"}
    </span>
  );
}
