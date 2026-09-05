import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, type Variants } from "motion/react";

import { useInterventionExecution } from "../features/intervention/useInterventionExecution";
import { ConsultationLayout } from "../layouts";
import { APP_PATHS } from "../routes";
import type { RecordInterventionEventPayload } from "../services/api/contracts";

const INTERVENTION_ENTRY_VIDEO_URI = "/digital-human/intervention-v1/intervention-entry-001.webm";

function requestBrowserFullscreen() {
  if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
    void document.documentElement.requestFullscreen().catch(() => undefined);
  }
}

const buttonVariants = {
  initial: { y: 0 },
  float: {
    y: [-5, 5, -5],
    transition: {
      duration: 4,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
  hover: {
    scale: 1.05,
    rotate: [-1, 1, -1, 0],
    transition: {
      rotate: {
        duration: 0.3,
        ease: "easeInOut",
      },
    },
  },
  tap: {
    scale: 0.95,
  },
} satisfies Variants;

type ActionButtonProps = {
  text: string;
  delay: number;
  onClick?: () => void;
  disabled?: boolean;
};

function ActionButton({ text, delay, onClick, disabled = false }: ActionButtonProps) {
  return (
    <motion.button
      type="button"
      variants={buttonVariants}
      initial="initial"
      animate="float"
      whileHover={disabled ? undefined : "hover"}
      whileTap={disabled ? undefined : "tap"}
      onClick={disabled ? undefined : onClick}
      style={{ animationDelay: `${delay}s` }}
      className={`group relative flex h-[64px] w-[280px] items-center justify-center overflow-visible rounded-[30px] outline-none md:h-[76px] md:w-[340px] ${
        disabled ? "cursor-not-allowed opacity-70" : ""
      }`}
    >
      <div className="pointer-events-none absolute -inset-6 z-0 opacity-50 transition-opacity duration-500 group-hover:opacity-100">
        <div className="absolute left-[10%] top-[10%] h-1.5 w-1.5 animate-[pulse_2s_ease-in-out_infinite] rounded-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
        <div className="absolute right-[15%] top-[20%] h-1 w-1 animate-[pulse_1.5s_ease-in-out_infinite_0.3s] rounded-full bg-white shadow-[0_0_5px_rgba(255,255,255,0.8)]" />
        <div className="absolute bottom-[20%] left-[25%] h-2 w-2 animate-[pulse_2.5s_ease-in-out_infinite_0.7s] rounded-full bg-blue-100 shadow-[0_0_10px_rgba(255,255,255,0.9)]" />
        <div className="absolute bottom-[10%] right-[10%] h-1 w-1 animate-[pulse_1.8s_ease-in-out_infinite_0.5s] rounded-full bg-purple-100 shadow-[0_0_8px_rgba(255,255,255,0.8)]" />
      </div>

      <div className="pointer-events-none absolute inset-0 z-10 rounded-[30px] bg-gradient-to-r from-blue-300 via-indigo-200 to-purple-300 opacity-0 blur-xl transition-opacity duration-500 group-hover:opacity-40" />

      <div className="absolute inset-0 z-20 flex items-center justify-center overflow-hidden rounded-[30px] border border-white/30 bg-white/10 shadow-[0_8px_32px_rgba(31,38,135,0.1),inset_0_4px_24px_rgba(255,255,255,0.2)] backdrop-blur-xl">
        <div className="pointer-events-none absolute inset-0 -translate-x-full skew-x-12 bg-gradient-to-r from-transparent via-white/40 to-transparent group-hover:animate-[shimmer_1.5s_infinite]" />
        <div className="absolute inset-x-4 top-0 h-[1px] bg-gradient-to-r from-transparent via-white/60 to-transparent" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-white/20 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />

        <span className="text-xl font-semibold tracking-[0.2em] text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)] md:text-2xl">
          {text}
        </span>
      </div>
    </motion.button>
  );
}

export default function InterventionPage() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const { buildRouteState, sessionError, trackEvent } = useInterventionExecution({
    pageTag: "intervention-landing",
    openEvent: {
      event_type: "module_opened",
      payload: {
        page: "intervention-landing",
      },
    },
  });

  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }

    void video.play().catch(() => undefined);
  }, []);

  const handleSelectExperience = async (
    route: string,
    eventPayload: RecordInterventionEventPayload,
  ) => {
    const sessionId = await trackEvent(eventPayload);
    if (!sessionId) {
      return;
    }

    navigate(route, {
      state: buildRouteState({
        interventionSessionId: sessionId,
      }),
    });
  };

  return (
    <ConsultationLayout backgroundImage="/TKbg.png" title="调节干预">
      <div className="relative flex h-full w-full flex-col items-center justify-end overflow-hidden pb-6 md:pb-9">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/40" />

        <div className="absolute inset-x-0 bottom-0 top-16 flex items-end justify-center">
          <video
            ref={videoRef}
            src={INTERVENTION_ENTRY_VIDEO_URI}
            playsInline
            preload="auto"
            className="h-[92%] md:h-[98%] max-w-none object-contain object-bottom scale-[1.08] md:scale-[1.15] drop-shadow-2xl"
          />
        </div>

        <div className="relative z-10 mb-7 w-full max-w-4xl px-6 text-center text-white">
          <p className="text-sm uppercase tracking-[0.45em] text-white/75">Intervention</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[0.12em] md:text-5xl">选择一种调节方式</h1>
          {sessionError ? <p className="mt-4 text-base text-amber-200/90">{sessionError}</p> : null}
        </div>

        <div className="perspective-[1000px] relative z-10 flex w-full max-w-6xl flex-col items-center justify-center gap-7 px-6 md:flex-row md:gap-14">
          <ActionButton
            text="看一段视频"
            delay={0}
            onClick={() =>
              void handleSelectExperience(APP_PATHS.interventionVideo, {
                event_type: "experience_selected",
                program_id: "guided-video",
                program_title: "视频调节",
                delivery_mode: "video",
                payload: { destination: "video" },
              })
            }
          />
          <ActionButton
            text="听一段诗歌"
            delay={0.2}
            onClick={() => {
              requestBrowserFullscreen();
              void handleSelectExperience(APP_PATHS.interventionStory, {
                event_type: "experience_selected",
                program_id: "poetry-experience",
                program_title: "诗歌沉浸朗读",
                delivery_mode: "poetry",
                payload: { destination: "poetry" },
              });
            }}
          />
        </div>
      </div>
    </ConsultationLayout>
  );
}
