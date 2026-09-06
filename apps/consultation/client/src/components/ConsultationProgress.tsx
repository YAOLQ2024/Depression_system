import { Check } from "lucide-react";
import { cn } from "../lib/utils";

const DEFAULT_STEPS = ["问候说明", "主诉采集", "症状筛查", "风险筛查"];

type ConsultationProgressProps = {
  currentStep?: number;
  currentStageOrder?: number | null;
  steps?: string[];
};

export function ConsultationProgress({
  currentStep,
  currentStageOrder,
  steps = DEFAULT_STEPS,
}: ConsultationProgressProps) {
  const resolvedCurrentStep = currentStageOrder ?? currentStep ?? 1;

  return (
    <div className="z-10 mx-auto mt-0 flex w-fit max-w-full items-center justify-center overflow-x-auto px-[clamp(12px,1.25vw,28px)] py-[clamp(4px,0.4vw,10px)]">
      {steps.map((step, idx) => {
        const stepNum = idx + 1;
        const isCompleted = stepNum < resolvedCurrentStep;
        const isActive = stepNum === resolvedCurrentStep;
        const isFuture = stepNum > resolvedCurrentStep;

        return (
          <div key={step} className="flex shrink-0 items-center">
            <div className={cn(
              "flex shrink-0 items-center gap-[clamp(6px,0.55vw,14px)] transition-colors",
              isActive ? "text-primary-600" : isFuture ? "text-slate-400" : "text-slate-700"
            )}>
              <div className={cn(
                "flex h-[clamp(26px,2vw,44px)] w-[clamp(26px,2vw,44px)] shrink-0 items-center justify-center rounded-full text-[clamp(11px,0.8vw,18px)] text-white shadow-md transition-all",
                isActive ? "bg-primary-500 shadow-primary-500/50 ring-[clamp(2px,0.16vw,4px)] ring-primary-100" : isFuture ? "bg-slate-300" : "bg-slate-700"
              )}>
                {isCompleted ? <Check className="h-[clamp(13px,1.15vw,24px)] w-[clamp(13px,1.15vw,24px)]" /> : stepNum}
              </div>
              <span className="whitespace-nowrap text-[clamp(11px,0.9vw,20px)] font-bold tracking-wide drop-shadow-sm">{step}</span>
            </div>
            {idx < steps.length - 1 && (
              <div className="mx-[clamp(6px,1vw,24px)] w-[clamp(28px,5vw,96px)] shrink-0 border-t-[clamp(1.5px,0.12vw,3px)] border-dashed border-slate-300/80"></div>
            )}
          </div>
        );
      })}
    </div>
  );
}
