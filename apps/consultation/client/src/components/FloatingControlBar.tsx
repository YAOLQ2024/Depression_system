import { Mic, CheckCircle } from "lucide-react";
import { cn } from "../lib/utils";

interface FloatingControlBarProps {
  isRecording: boolean;
  onToggleRecord: () => void;
  onEnd: () => void;
  recordDisabled?: boolean;
  endDisabled?: boolean;
  recordLabel?: string;
  endLabel?: string;
}

export function FloatingControlBar({
  isRecording,
  onToggleRecord,
  onEnd,
  recordDisabled = false,
  endDisabled = false,
  recordLabel = "语音输入",
  endLabel = "进入量表评估",
}: FloatingControlBarProps) {
  return (
    <div className="mx-auto z-30 relative group pointer-events-auto">
      <div className="bg-white/20 backdrop-blur-3xl px-6 py-3 flex items-center justify-center gap-6 rounded-full border border-white/40 shadow-[0_4px_20px_rgba(0,0,0,0.1)] relative">
        <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-white/20 pointer-events-none rounded-full"></div>
        
        <button 
          onClick={onToggleRecord}
          disabled={recordDisabled}
          className={cn(
            "flex items-center gap-2 text-sm font-medium transition-all relative z-10",
            recordDisabled
              ? "cursor-not-allowed text-white/35"
              : isRecording
                ? "pointer-events-auto cursor-pointer text-primary-400"
                : "pointer-events-auto cursor-pointer text-white/90 hover:text-white",
          )}
        >
          <Mic className={cn("w-4 h-4", isRecording && "animate-pulse")} />
          <span>{recordLabel}</span>
        </button>

        <div className="w-px h-4 bg-white/30 relative z-10"></div>

        <button 
          onClick={onEnd}
          disabled={endDisabled}
          className={cn(
            "flex items-center gap-2 text-sm font-medium transition-all relative z-10",
            endDisabled
              ? "cursor-not-allowed text-white/35"
              : "pointer-events-auto cursor-pointer text-white/90 hover:text-white",
          )}
        >
          <CheckCircle className="w-4 h-4" />
          <span>{endLabel}</span>
        </button>
      </div>
    </div>
  );
}
