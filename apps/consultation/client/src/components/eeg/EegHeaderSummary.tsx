import {
  clampToPercent,
  getEegEmotionConfig,
  getEegEmotionScore,
  hasEegEmotionResult,
  resolveEegEmotionStatusLabel,
  resolvePrimaryEegEmotionLabel,
  withAlpha,
  type EegEmotionDistributionItem,
} from "./eegEmotionPresentation";

type EegHeaderSummaryProps = {
  distribution: EegEmotionDistributionItem[];
  primaryLabel?: string | null;
  primaryScore?: number | null;
  deviceStatus?: string | null;
  errorMessage?: string | null;
};

export function EegHeaderSummary({
  distribution,
  primaryLabel,
  primaryScore,
  deviceStatus,
  errorMessage,
}: EegHeaderSummaryProps) {
  const hasResult = hasEegEmotionResult(distribution, primaryLabel);
  const resolvedPrimaryLabel = resolvePrimaryEegEmotionLabel(distribution, primaryLabel);

  if (!hasResult || !resolvedPrimaryLabel) {
    return (
      <div className="min-w-0 text-right">
        <div className="text-[12px] font-medium text-slate-300">
          {resolveEegEmotionStatusLabel(deviceStatus, errorMessage)}
        </div>
      </div>
    );
  }

  const primaryAccent = getEegEmotionConfig(resolvedPrimaryLabel).accentColor;
  const resolvedPrimaryScore =
    typeof primaryScore === "number" ? primaryScore : getEegEmotionScore(distribution, resolvedPrimaryLabel);

  return (
    <div className="min-w-0 text-right">
      <div
        className="truncate text-[15px] font-semibold tracking-tight"
        style={{
          color: primaryAccent,
          textShadow: `0 0 16px ${withAlpha(primaryAccent, 0.18)}`,
        }}
      >
        {resolvedPrimaryLabel} · {clampToPercent(resolvedPrimaryScore)}%
      </div>
      <div className="mt-0.5 flex flex-wrap justify-end gap-x-1 gap-y-0.5 text-[12px] leading-4">
        {distribution.map((item, index) => {
          const accentColor = getEegEmotionConfig(item.label).accentColor;
          return (
            <span key={item.label} className="inline-flex items-center">
              <span className="font-medium" style={{ color: accentColor }}>
                {item.label}
                {clampToPercent(item.score)}%
              </span>
              {index < distribution.length - 1 ? <span className="px-1 text-slate-500/80">；</span> : null}
            </span>
          );
        })}
      </div>
    </div>
  );
}
