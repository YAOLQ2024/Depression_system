import { CheckCheck, ChevronRight } from "lucide-react";

type FlowCompletionStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function FlowCompletionState({
  title,
  description,
  actionLabel,
  onAction,
}: FlowCompletionStateProps) {
  return (
    <>
      <style>{`
        @keyframes mcs-completion-orbit {
          0% { transform: rotate(0deg) translateX(0) scale(1); opacity: 0.45; }
          50% { transform: rotate(180deg) translateX(10px) scale(1.08); opacity: 0.8; }
          100% { transform: rotate(360deg) translateX(0) scale(1); opacity: 0.45; }
        }

        @keyframes mcs-completion-shimmer {
          0% { transform: translateX(-120%) skewX(-18deg); opacity: 0; }
          20% { opacity: 0.75; }
          100% { transform: translateX(140%) skewX(-18deg); opacity: 0; }
        }

        @keyframes mcs-completion-float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-6px); }
        }
      `}</style>
      <div className="relative flex h-full w-full items-center justify-center overflow-hidden px-6 text-center text-white">
        <div className="pointer-events-none absolute inset-0 opacity-80">
          <div className="absolute left-1/2 top-[18%] h-48 w-48 -translate-x-1/2 rounded-full bg-emerald-400/14 blur-[90px]" />
          <div className="absolute left-[24%] top-[42%] h-36 w-36 rounded-full bg-sky-400/12 blur-[80px]" />
          <div className="absolute right-[22%] top-[44%] h-40 w-40 rounded-full bg-cyan-300/10 blur-[90px]" />
        </div>

        <div className="relative z-10 flex max-w-2xl flex-col items-center">
          <div className="relative mb-8 flex h-36 w-36 items-center justify-center [animation:mcs-completion-float_4.2s_ease-in-out_infinite]">
            <div className="absolute inset-0 rounded-full border border-emerald-300/20 bg-[radial-gradient(circle,rgba(52,211,153,0.2),rgba(16,185,129,0.05)_55%,transparent_72%)] blur-sm" />
            <div className="absolute inset-[14px] rounded-full border border-white/10" />
            <div
              className="absolute inset-[6px] rounded-full border border-emerald-200/35"
              style={{ animation: "mcs-completion-orbit 6.6s linear infinite" }}
            />
            <div className="absolute h-4 w-4 -translate-y-[52px] rounded-full bg-emerald-200/80 blur-[2px]" />
            <CheckCheck className="relative h-20 w-20 text-emerald-300 drop-shadow-[0_0_24px_rgba(110,231,183,0.55)]" strokeWidth={2.2} />
          </div>

          <p className="text-[2.15rem] font-semibold tracking-[0.03em] text-white drop-shadow-[0_10px_30px_rgba(15,23,42,0.28)]">
            {title}
          </p>
          <p className="mt-4 max-w-xl text-base leading-8 text-slate-100/88">
            {description}
          </p>

          {actionLabel && onAction ? (
            <button
              onClick={onAction}
              className="group relative mt-10 inline-flex overflow-hidden rounded-full p-[1px] shadow-[0_18px_50px_rgba(99,102,241,0.28)] transition-transform duration-300 hover:scale-[1.03]"
            >
              <span className="absolute inset-0 rounded-full bg-[linear-gradient(120deg,rgba(96,165,250,0.95),rgba(99,102,241,0.98),rgba(168,85,247,0.95),rgba(96,165,250,0.95))]" />
              <span className="absolute inset-0 rounded-full opacity-80 blur-md bg-[linear-gradient(120deg,rgba(96,165,250,0.45),rgba(99,102,241,0.4),rgba(168,85,247,0.4),rgba(96,165,250,0.45))]" />
              <span
                className="pointer-events-none absolute inset-y-0 left-0 w-24 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.9),transparent)]"
                style={{ animation: "mcs-completion-shimmer 2.9s ease-in-out infinite" }}
              />
              <span className="relative inline-flex items-center gap-3 rounded-full bg-[linear-gradient(180deg,rgba(255,255,255,0.16),rgba(255,255,255,0.06))] px-9 py-4 text-base font-semibold text-white backdrop-blur-xl">
                <span className="absolute inset-0 rounded-full bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.3),transparent_60%)] opacity-70" />
                <ChevronRight className="relative h-5 w-5 transition-transform duration-300 group-hover:translate-x-0.5" />
                <span className="relative">{actionLabel}</span>
              </span>
            </button>
          ) : null}
        </div>
      </div>
    </>
  );
}
