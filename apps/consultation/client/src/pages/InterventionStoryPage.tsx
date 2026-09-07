import { useEffect, useEffectEvent, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  INTERVENTION_MODERN_POETRY_IFRAME_SRC,
  INTERVENTION_POETRY_JOURNEY_IFRAME_SRC,
} from "../features/intervention/embeddedExperiences";
import { useInterventionExecution } from "../features/intervention/useInterventionExecution";
import { APP_PATHS } from "../routes";

type PoetryExperience = {
  id: "poetry-journey" | "modern-poetry";
  title: string;
  label: string;
  description: string;
  iframeSrc: string;
};

const POETRY_EXPERIENCES: PoetryExperience[] = [
  {
    id: "modern-poetry",
    title: "最好的你现代诗朗读",
    label: "现代诗 · 最好的你",
    description: "在田园风声中，听一首写给自己的诗。",
    iframeSrc: INTERVENTION_MODERN_POETRY_IFRAME_SRC,
  },
  {
    id: "poetry-journey",
    title: "山水诗境古诗词朗读",
    label: "古诗词 · 山水诗境",
    description: "在山水之间聆听《苔》《菜根谭》与《定风波》。",
    iframeSrc: INTERVENTION_POETRY_JOURNEY_IFRAME_SRC,
  },
];

const POETRY_BACKGROUND_VIDEO_URLS = [
  "/intervention/stories/poetry-journey/assets/mountain-background.mp4?v=web-optimized",
  "/intervention/stories/modern-poetry/assets/pastoral-background.mp4?v=web-optimized",
];

function requestBrowserFullscreen() {
  if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
    void document.documentElement.requestFullscreen().catch(() => undefined);
  }
}

export default function InterventionStoryPage() {
  const navigate = useNavigate();
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [activeExperience, setActiveExperience] = useState<PoetryExperience | null>(null);
  const { buildRouteState, sessionError, trackEvent } = useInterventionExecution({
    pageTag: "intervention-poetry",
  });

  useEffect(() => {
    const preloadLinks = POETRY_BACKGROUND_VIDEO_URLS.map((href) => {
      const link = document.createElement("link");
      link.rel = "preload";
      link.as = "video";
      link.href = href;
      document.head.appendChild(link);
      return link;
    });
    return () => preloadLinks.forEach((link) => link.remove());
  }, []);

  const returnToLanding = useEffectEvent((reason: "iframe_message" | "return_button") => {
    const experience = activeExperience;
    void trackEvent({
      event_type: "experience_exited",
      program_id: experience?.id ?? "poetry-experience",
      program_title: experience?.title ?? "诗歌沉浸朗读",
      delivery_mode: "poetry",
      payload: { page: "intervention-poetry", reason, destination: "intervention-landing" },
    });
    if (document.fullscreenElement) {
      void document.exitFullscreen().catch(() => undefined);
    }
    navigate(APP_PATHS.intervention, { state: buildRouteState() });
  });

  const returnToPoetrySelection = useEffectEvent(() => {
    const experience = activeExperience;
    if (!experience) {
      return;
    }
    void trackEvent({
      event_type: "experience_exited",
      program_id: experience.id,
      program_title: experience.title,
      delivery_mode: "poetry",
      payload: { page: "intervention-poetry", reason: "return_to_selection", destination: "poetry-selection" },
    });
    setActiveExperience(null);
  });

  const handleIframeMessage = useEffectEvent((event: MessageEvent) => {
    if (
      event.origin !== window.location.origin ||
      event.source !== iframeRef.current?.contentWindow ||
      !activeExperience
    ) {
      return;
    }

    if (event.data?.type === "intervention-return-to-poetry-selection") {
      returnToPoetrySelection();
      return;
    }

    if (event.data?.type === "intervention-exit") {
      returnToLanding("iframe_message");
      return;
    }

    if (event.data?.type === "intervention-story-event") {
      const lifecycleEvent =
        typeof event.data.event === "string"
          ? event.data.event
          : typeof event.data.action === "string"
            ? event.data.action
            : "interaction";
      void trackEvent({
        event_type: "experience_progressed",
        program_id: activeExperience.id,
        program_title: activeExperience.title,
        delivery_mode: "poetry",
        payload: {
          page: "intervention-poetry",
          poem_type: activeExperience.id,
          lifecycle_event: lifecycleEvent,
        },
      });
    }
  });

  useEffect(() => {
    window.addEventListener("message", handleIframeMessage);
    return () => window.removeEventListener("message", handleIframeMessage);
  }, []);

  const selectExperience = async (experience: PoetryExperience) => {
    requestBrowserFullscreen();
    const sessionId = await trackEvent({
      event_type: "experience_opened",
      program_id: experience.id,
      program_title: experience.title,
      delivery_mode: "poetry",
      payload: { page: "intervention-poetry", poem_type: experience.id },
    });
    if (sessionId) {
      setActiveExperience(experience);
    }
  };

  if (activeExperience) {
    return (
      <div className="fixed inset-0 z-[100] overflow-hidden bg-slate-950">
        <iframe
          ref={iframeRef}
          title={activeExperience.title}
          src={activeExperience.iframeSrc}
          allow="autoplay; fullscreen"
          className="h-full w-full border-0 bg-slate-950"
        />
      </div>
    );
  }

  return (
    <main className="fixed inset-0 z-[100] flex overflow-hidden bg-[#101812] px-6 py-8 text-white sm:px-10">
      <video
        className="pointer-events-none absolute inset-0 h-full w-full object-cover"
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        aria-hidden="true"
      >
        <source src="/intervention/poetry-selection/cover.mp4?v=web-optimized" type="video/mp4" />
      </video>
      <div className="relative z-10 mx-auto mb-auto mt-[clamp(2rem,6vh,6rem)] w-full max-w-5xl">
        <button
          type="button"
          onClick={() => returnToLanding("return_button")}
          className="mb-10 rounded-full border border-white/60 bg-slate-950/65 px-7 py-3 text-base font-semibold text-white shadow-[0_10px_30px_rgba(0,0,0,0.42)] transition hover:bg-slate-950/85 hover:text-white"
        >
          ← 返回调节干预
        </button>
        <p className="text-xs font-medium uppercase tracking-[0.42em] text-emerald-100/90">Poetry Experience</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-[0.12em] text-white drop-shadow-[0_3px_16px_rgba(0,0,0,0.8)] sm:text-5xl">听一段诗歌</h1>
        <p className="mt-5 max-w-xl text-base font-medium leading-7 text-white/90">选择一首诗，在全屏沉浸体验中聆听。</p>
        {sessionError ? <p className="mt-4 text-sm text-amber-200">{sessionError}</p> : null}
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {POETRY_EXPERIENCES.map((experience) => (
            <button
              key={experience.id}
              type="button"
              onClick={() => void selectExperience(experience)}
              className="group rounded-[32px] border border-white/35 bg-slate-950/62 p-7 text-left shadow-[0_24px_60px_rgba(0,0,0,0.48)] backdrop-blur-sm transition hover:-translate-y-1 hover:bg-slate-950/78"
            >
              <p className="text-sm font-medium tracking-[0.14em] text-emerald-100">{experience.label}</p>
              <p className="mt-5 text-base font-medium leading-7 text-white/90">{experience.description}</p>
              <span className="mt-8 inline-block text-sm font-medium text-white">全屏聆听 →</span>
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
