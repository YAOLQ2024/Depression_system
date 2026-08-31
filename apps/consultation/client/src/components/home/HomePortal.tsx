import { motion } from "motion/react";

type HomePortalProps = {
  activeMenuTitle: string;
  onAvatarClick: () => void;
};

/** Bright-theme counterpart of the reference page's oversized 3/4 avatar chamber. */
export function HomePortal({ activeMenuTitle, onAvatarClick }: HomePortalProps) {
  return (
    <div className="pointer-events-none relative flex h-full w-full select-none items-center justify-start">
      <div className="relative mt-[4vh] aspect-square w-[52vw] min-w-[720px] max-w-[940px] -ml-[8vw] sm:-ml-[6vw]">
        <div className="pointer-events-none absolute -inset-10 rounded-full bg-[radial-gradient(circle,rgba(125,211,252,0.18)_0%,rgba(165,180,252,0.1)_48%,transparent_75%)] opacity-70 blur-3xl" />

        {/* Deliberately transparent: this is now only an orbital frame, never a white avatar mask. */}
        <div className="relative h-full w-full rounded-full border-2 border-sky-300/75 shadow-[0_0_34px_rgba(56,189,248,0.32)]">
          <div className="pointer-events-none absolute inset-x-12 top-0 h-[2px] bg-gradient-to-r from-transparent via-sky-200 to-transparent blur-[1px]" />
          <div className="pointer-events-none absolute inset-8 rounded-full border-2 border-sky-500/55" />
          <div className="pointer-events-none absolute inset-20 rounded-full border-2 border-blue-500/55 border-dashed" />
          <div className="pointer-events-none absolute inset-36 rounded-full border-2 border-indigo-500/45" />

          <motion.div
            className="pointer-events-none absolute inset-2 rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 180, repeat: Infinity, ease: "linear" }}
          >
            <svg className="h-full w-full" viewBox="0 0 800 800" aria-hidden="true">
              <circle cx="400" cy="400" r="394" fill="none" stroke="rgba(14,165,233,0.84)" strokeWidth="2.5" strokeDasharray="5 14" />
              <circle cx="400" cy="400" r="380" fill="none" stroke="rgba(79,70,229,0.7)" strokeWidth="1.8" strokeDasharray="2 7" />
            </svg>
          </motion.div>

          <div className="pointer-events-auto absolute inset-0 flex items-end justify-center pb-8 sm:pb-12">
            <motion.button
              type="button"
              onClick={onAvatarClick}
              className="relative h-[89%] cursor-pointer focus:outline-none"
              animate={{ y: [0, -5, 0] }}
              transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut" }}
              title={`进入${activeMenuTitle}`}
            >
              <img
                src="/home-digital-human.png"
                alt="数字人心理助手"
                fetchPriority="high"
                className="h-full w-auto max-w-none object-contain object-bottom drop-shadow-[0_28px_48px_rgba(15,23,42,0.26)]"
              />
            </motion.button>
          </div>
        </div>

        <div className="pointer-events-none absolute inset-0 rounded-full shadow-[inset_0_0_24px_rgba(14,165,233,0.12),0_0_34px_rgba(59,130,246,0.24)]" />

        <div className="pointer-events-none absolute inset-y-0 right-0 -mt-[4vh] -translate-y-10 sm:-translate-y-14 lg:-translate-y-16">
          <div className="absolute -right-3 top-[22%] h-3 w-3 rounded-full bg-sky-400/65 ring-4 ring-sky-400/15 shadow-[0_0_10px_#38bdf8]" />
          <div className="absolute -right-5 top-[36%] h-3.5 w-3.5 rounded-full bg-sky-400/75 ring-4 ring-sky-400/20 shadow-[0_0_12px_#38bdf8]" />
          <div className="absolute -right-6 top-[50%] h-4 w-4 -translate-y-1/2 rounded-full bg-sky-300 ring-6 ring-sky-400/30 shadow-[0_0_16px_#38bdf8]" />
          <div className="absolute -right-5 top-[64%] h-3.5 w-3.5 rounded-full bg-sky-400/75 ring-4 ring-sky-400/20 shadow-[0_0_12px_#38bdf8]" />
          <div className="absolute -right-3 top-[78%] h-3 w-3 rounded-full bg-sky-400/65 ring-4 ring-sky-400/15 shadow-[0_0_10px_#38bdf8]" />
        </div>
      </div>
    </div>
  );
}
