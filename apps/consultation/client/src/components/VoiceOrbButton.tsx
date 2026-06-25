import { motion } from "motion/react";

import { SiriOrb } from "./smoothui/ui/SiriOrb";
import { cn } from "../lib/utils";

interface VoiceOrbButtonProps {
  isRecording: boolean;
  onToggleRecord: () => void;
  disabled?: boolean;
  label: string;
  className?: string;
}

export function VoiceOrbButton({
  isRecording,
  onToggleRecord,
  disabled = false,
  label,
  className,
}: VoiceOrbButtonProps) {
  return (
    <div className={cn("pointer-events-auto flex items-center justify-center", className)}>
      <motion.button
        type="button"
        aria-label={label}
        aria-pressed={isRecording}
        disabled={disabled}
        onClick={onToggleRecord}
        whileHover={disabled ? undefined : { scale: 1.04 }}
        whileTap={disabled ? undefined : { scale: 0.96 }}
        transition={{ type: "spring", stiffness: 280, damping: 18 }}
        className={cn(
          "group relative flex h-[128px] w-[128px] items-center justify-center overflow-visible rounded-full transition-[opacity,filter] duration-300",
          disabled ? "cursor-not-allowed opacity-55" : "cursor-pointer",
        )}
      >
        <span className="sr-only">{label}</span>
        <motion.span
          aria-hidden
          className="pointer-events-none absolute bottom-[-18px] left-1/2 h-10 w-[96px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(124,58,237,0.26),rgba(99,102,241,0.18)_46%,transparent_76%)] blur-xl"
          animate={{
            opacity: isRecording ? [0.24, 0.4, 0.24] : [0.12, 0.18, 0.12],
            scaleX: isRecording ? [0.96, 1.1, 0.96] : [0.99, 1.03, 0.99],
          }}
          transition={{
            duration: isRecording ? 2.4 : 5.2,
            ease: "easeInOut",
            repeat: Number.POSITIVE_INFINITY,
          }}
        />
        <motion.span
          aria-hidden
          className="pointer-events-none absolute inset-[-24px] rounded-full bg-[radial-gradient(circle,rgba(167,139,250,0.34),rgba(129,140,248,0.22)_36%,transparent_72%)] blur-2xl"
          animate={{
            opacity: disabled && !isRecording ? 0.2 : isRecording ? [0.24, 0.52, 0.24] : [0.14, 0.26, 0.14],
            scale: isRecording ? [0.95, 1.08, 0.95] : [0.99, 1.03, 0.99],
          }}
          transition={{
            duration: isRecording ? 2.8 : 5.6,
            ease: "easeInOut",
            repeat: Number.POSITIVE_INFINITY,
          }}
        />
        <div aria-hidden className="relative h-[122px] w-[122px]" style={{ perspective: "1400px" }}>
          <div className="absolute inset-x-[9px] bottom-[4px] h-[24px] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(109,40,217,0.24),rgba(129,140,248,0.14)_56%,transparent_78%)] blur-md" />
          <motion.div
            animate={{
              rotateZ: isRecording ? [0, 1.8, -1.8, 0] : [0, 0.6, 0],
              y: isRecording ? [0, -2, 0] : [0, -0.6, 0],
            }}
            transition={{
              duration: isRecording ? 5.8 : 10.5,
              ease: "easeInOut",
              repeat: Number.POSITIVE_INFINITY,
            }}
            className="relative h-full w-full [transform-style:preserve-3d]"
            style={{ transform: "rotateX(22deg) rotateY(-10deg)" }}
          >
            <div className="absolute inset-0 overflow-hidden rounded-full shadow-[0_18px_38px_rgba(109,40,217,0.22),0_0_26px_rgba(167,139,250,0.22)]">
              <SiriOrb
                size="122px"
                animationDuration={isRecording ? 6.4 : 11.8}
                className={cn("scale-[1.02] saturate-[1.18] brightness-[1.02]", disabled && !isRecording && "opacity-72")}
                colors={{
                  bg: "oklch(81% 0.04 295)",
                  c1: "oklch(67% 0.2 314)",
                  c2: "oklch(62% 0.18 274)",
                  c3: "oklch(72% 0.13 245)",
                }}
              />
              <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle_at_26%_18%,rgba(255,255,255,0.36),transparent_18%),radial-gradient(circle_at_62%_68%,rgba(96,165,250,0.12),transparent_28%),radial-gradient(circle_at_52%_46%,rgba(167,139,250,0.18),transparent_24%),linear-gradient(180deg,rgba(255,255,255,0.16),transparent_28%,rgba(124,58,237,0.1)_84%)]" />
              <motion.div
                animate={{
                  opacity: isRecording ? [0.38, 0.62, 0.38] : [0.28, 0.4, 0.28],
                  scale: isRecording ? [0.96, 1.06, 0.96] : [1, 1.02, 1],
                }}
                transition={{
                  duration: isRecording ? 2.6 : 5.8,
                  ease: "easeInOut",
                  repeat: Number.POSITIVE_INFINITY,
                }}
                className="absolute inset-[35px] rounded-full bg-[radial-gradient(circle_at_40%_36%,rgba(255,255,255,0.16),rgba(196,181,253,0.18)_24%,rgba(139,92,246,0.18)_54%,transparent_76%)] blur-[1px]"
              />
              <div className="absolute left-[13px] top-[10px] h-[44px] w-[30px] rotate-[-24deg] rounded-full bg-[linear-gradient(180deg,rgba(255,255,255,0.72),rgba(255,255,255,0.1)_62%,transparent)] blur-[1px]" />
              <div className="absolute right-[22px] top-[20px] h-[16px] w-[14px] rounded-full bg-white/26 blur-sm" />
              <div className="absolute inset-x-[21px] top-[10px] h-[22px] rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.42),rgba(255,255,255,0.06)_62%,transparent_82%)] blur-md" />
              <div className="absolute inset-x-[18px] bottom-[13px] h-[24px] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(109,40,217,0.18),transparent_72%)] blur-sm" />
            </div>
          </motion.div>
        </div>
      </motion.button>
    </div>
  );
}
