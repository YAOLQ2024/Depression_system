import { Camera, Mic, MicOff, TriangleAlert } from "lucide-react";
import { useEffect, useRef, type RefObject } from "react";

import { cn } from "../lib/utils";
import type { MediaDeviceStatusTone } from "../lib/mediaDeviceFeedback";
import { isPerformanceMode } from "../lib/runtimeConfig";

interface CameraPreviewProps {
  className?: string;
  videoRef?: RefObject<HTMLVideoElement | null>;
  stream?: MediaStream | null;
  cameraReady?: boolean;
  audioActive?: boolean;
  title?: string;
  headlineText?: string;
  detailText?: string;
  errorText?: string | null;
  statusTone?: MediaDeviceStatusTone;
  audioStatusText?: string;
  mirrored?: boolean;
}

export function CameraPreview({
  className,
  videoRef,
  stream = null,
  cameraReady = false,
  audioActive = false,
  title = "摄像头监测中",
  headlineText = "等待摄像头授权",
  detailText = "等待视频流",
  errorText = null,
  statusTone = "pending",
  audioStatusText,
  mirrored = true,
}: CameraPreviewProps) {
  const fallbackVideoRef = useRef<HTMLVideoElement | null>(null);
  const resolvedVideoRef = videoRef || fallbackVideoRef;
  const performanceMode = isPerformanceMode();

  useEffect(() => {
    const videoElement = resolvedVideoRef.current;
    if (!videoElement) {
      return;
    }
    videoElement.srcObject = stream;
    if (stream) {
      void videoElement.play().catch(() => undefined);
    }
  }, [resolvedVideoRef, stream]);

  const statusDotClass =
    statusTone === "ready"
      ? "bg-green-400 animate-pulse"
      : statusTone === "error"
        ? "bg-rose-400"
        : "bg-amber-300";

  const previewIconClass =
    statusTone === "error" ? "text-rose-200/90" : statusTone === "warning" ? "text-amber-100/90" : "text-sky-100/80";

  return (
    <div
      className={cn(
        "relative z-50 flex flex-col overflow-hidden border border-white/60",
        performanceMode ? "rounded-2xl bg-slate-950 shadow-none" : "glass-card shadow-lg",
        className,
      )}
    >
      <div
        className={cn(
          "absolute top-3 left-3 z-10 flex items-center gap-1.5 rounded-full px-2 py-1",
          performanceMode ? "bg-black/75" : "bg-black/35 backdrop-blur-md",
        )}
      >
        <div className={cn("h-1.5 w-1.5 rounded-full", statusDotClass)} />
        <span className="text-[10px] font-medium tracking-wide text-white">{title}</span>
      </div>

      {cameraReady ? (
        <video
          ref={resolvedVideoRef}
          autoPlay
          muted
          playsInline
          className="h-full w-full object-cover"
          style={mirrored ? { transform: "scaleX(-1)" } : undefined}
        />
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-3 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.2),transparent_40%),linear-gradient(135deg,rgba(15,23,42,0.92),rgba(30,41,59,0.84))] px-5 text-center text-white">
          <div className="flex h-14 w-14 items-center justify-center rounded-full border border-white/15 bg-white/8">
            <Camera className={cn("h-6 w-6", previewIconClass)} />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium">{headlineText}</p>
            <p className="text-[11px] leading-5 text-slate-200/80">{errorText || detailText}</p>
          </div>
        </div>
      )}

      <div className="absolute bottom-2 inset-x-2 z-10 flex items-center justify-between gap-2">
        <div
          className={cn(
            "flex items-center gap-1 rounded-lg px-2 py-1.5",
            performanceMode ? "bg-black/80" : "bg-black/40 backdrop-blur-md",
          )}
        >
          {cameraReady ? <Camera className="h-3 w-3 text-emerald-300" /> : <TriangleAlert className="h-3 w-3 text-amber-300" />}
          <span className="text-[10px] text-white">{detailText}</span>
        </div>
        <div
          className={cn(
            "flex items-center gap-1 rounded-lg px-2 py-1.5",
            performanceMode ? "bg-black/80" : "bg-black/40 backdrop-blur-md",
          )}
        >
          {audioActive ? <Mic className="h-3 w-3 text-emerald-300" /> : <MicOff className="h-3 w-3 text-white/75" />}
          <span className="text-[10px] text-white">{audioStatusText || (audioActive ? "麦克风开启" : "麦克风待命")}</span>
        </div>
      </div>
    </div>
  );
}
