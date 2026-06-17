import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import type { RecordInterventionEventPayload } from "../../services/api/contracts";
import { useInterventionExecution } from "./useInterventionExecution";
import { ConsultationLayout } from "../../layouts";
import { APP_PATHS } from "../../routes";

type InterventionEmbeddedExperienceProps = {
  eyebrow: string;
  title: string;
  subtitle: string;
  iframeSrc: string;
  openEvent: RecordInterventionEventPayload;
};

export function InterventionEmbeddedExperience({
  eyebrow,
  title,
  subtitle,
  iframeSrc,
  openEvent,
}: InterventionEmbeddedExperienceProps) {
  const navigate = useNavigate();
  const { buildRouteState, sessionError } = useInterventionExecution({
    pageTag: iframeSrc,
    openEvent,
  });

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) {
        return;
      }

      if (event.data?.type === "intervention-exit") {
        navigate(APP_PATHS.intervention, {
          state: buildRouteState(),
        });
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [buildRouteState, navigate]);

  return (
    <ConsultationLayout backgroundImage="/bg.webp" title={title}>
      <div className="relative flex h-full w-full overflow-hidden bg-[radial-gradient(circle_at_top,rgba(130,181,255,0.16),transparent_42%),linear-gradient(180deg,rgba(10,16,31,0.18),rgba(10,16,31,0.78))]">
        <div className="mx-auto flex h-full w-full max-w-7xl flex-col gap-5 px-5 pb-6 pt-6 md:px-8">
          <div className="flex flex-col gap-4 rounded-[32px] border border-white/14 bg-white/8 px-5 py-5 shadow-[0_20px_50px_rgba(2,6,23,0.35)] backdrop-blur-xl md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-cyan-100/65">{eyebrow}</p>
              <h1 className="mt-3 text-2xl font-semibold tracking-[0.08em] text-white md:text-3xl">{title}</h1>
              <p className="mt-3 text-sm leading-6 text-white/70 md:text-base">{subtitle}</p>
            </div>

            <button
              type="button"
              onClick={() =>
                navigate(APP_PATHS.intervention, {
                  state: buildRouteState(),
                })
              }
              className="rounded-full border border-white/20 bg-white/8 px-4 py-2 text-sm text-white/88 transition hover:bg-white/14"
            >
              返回干预首页
            </button>
          </div>
          {sessionError ? <p className="text-sm text-amber-200/90">{sessionError}</p> : null}

          <div className="min-h-0 flex-1 overflow-hidden rounded-[32px] border border-white/14 bg-slate-950/38 shadow-[0_24px_60px_rgba(2,6,23,0.45)] backdrop-blur-xl">
            <iframe
              title={title}
              src={iframeSrc}
              allow="autoplay; fullscreen"
              className="h-full w-full border-0 bg-white"
            />
          </div>
        </div>
      </div>
    </ConsultationLayout>
  );
}
