import { useResultTheme, themeClasses } from "../theme-context";
import { cn } from "../../../lib/utils";

interface RingChartProps {
  score: number;
  maxScore?: number;
  label?: string;
  size?: number;
  strokeWidth?: number;
  color?: string;
  valueLabel?: string;
}

export function RingChart({
  score,
  maxScore = 100,
  label = "总体分数",
  size = 140,
  strokeWidth = 14,
  color = "#3B82F6",
  valueLabel,
}: RingChartProps) {
  const theme = useResultTheme();
  const t = themeClasses;

  const safeMaxScore = maxScore > 0 ? maxScore : 100;
  const clampedScore = Math.min(Math.max(score, 0), safeMaxScore);
  const radius = size / 2;
  const normalizedRadius = radius - strokeWidth;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (clampedScore / safeMaxScore) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg height={size} width={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          stroke={color}
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeOpacity={0.15}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke={color}
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          style={{ strokeDashoffset, transition: "stroke-dashoffset 1s ease-in-out" }}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          className="origin-center -rotate-90"
        />
      </svg>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("mb-0.5 text-xs font-semibold tracking-[0.08em]", t.scoreLabel[theme])}>{label}</span>
        <span className={cn("text-3xl font-bold leading-none", t.value[theme])}>{valueLabel || clampedScore}</span>
      </div>
    </div>
  );
}
