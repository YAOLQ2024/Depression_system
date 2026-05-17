import { Check } from "lucide-react";
import { cn } from "../lib/utils";

const DEFAULT_STEPS = ["问候说明", "主诉采集", "现病史", "风险筛查"];

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
    <div className="flex items-center justify-between w-full max-w-2xl z-10 mx-auto px-4 sm:px-6 py-1 mt-0">
      {steps.map((step, idx) => {
        const stepNum = idx + 1;
        const isCompleted = stepNum < resolvedCurrentStep;
        const isActive = stepNum === resolvedCurrentStep;
        const isFuture = stepNum > resolvedCurrentStep;

        return (
          <div key={step} className="flex items-center flex-1 last:flex-none">
            <div className={cn(
              "flex items-center gap-1.5 sm:gap-2 transition-colors flex-shrink-0",
              isActive ? "text-primary-600" : isFuture ? "text-slate-400" : "text-slate-700"
            )}>
              <div className={cn(
                "w-6 h-6 md:w-8 md:h-8 rounded-full flex items-center justify-center text-[10px] md:text-sm text-white shadow-md transition-all flex-shrink-0",
                isActive ? "bg-primary-500 shadow-primary-500/50 ring-[2px] md:ring-[3px] ring-primary-100" : isFuture ? "bg-slate-300" : "bg-slate-700"
              )}>
                {isCompleted ? <Check className="w-3 h-3 md:w-5 md:h-5" /> : stepNum}
              </div>
              <span className="text-[10px] sm:text-xs md:text-sm tracking-wide font-bold drop-shadow-sm whitespace-nowrap">{step}</span>
            </div>
            {/* Dashed line connector */}
            {idx < steps.length - 1 && (
              <div className="flex-1 border-t-[1.5px] md:border-t-[2px] border-dashed border-slate-300/80 mx-1 sm:mx-2 md:mx-4"></div>
            )}
          </div>
        );
      })}
    </div>
  );
}
