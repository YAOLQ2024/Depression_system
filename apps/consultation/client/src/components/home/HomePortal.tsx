import { motion } from "motion/react";
import { CometOrbit } from "./CometOrbit";

type HomePortalProps = {
  activeMenuTitle: string;
  onAvatarClick: () => void;
};

/** The original avatar placement with the AI Studio dual-track comet orbit. */
export function HomePortal({ activeMenuTitle, onAvatarClick }: HomePortalProps) {
  return (
    <div className="pointer-events-none relative flex h-full w-full select-none items-center justify-start">
      <div className="relative mt-[4vh] aspect-square w-[52vw] min-w-[720px] max-w-[940px] -ml-[8vw] sm:-ml-[6vw]">
        <div className="pointer-events-none absolute -inset-10 rounded-full bg-[radial-gradient(circle,rgba(125,211,252,0.18)_0%,rgba(165,180,252,0.1)_48%,transparent_75%)] opacity-70 blur-3xl" />

        <div className="relative h-full w-full rounded-full">
          <CometOrbit />

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

        <div className="pointer-events-none absolute inset-0 rounded-full shadow-[inset_0_0_20px_rgba(14,165,233,0.1),0_0_28px_rgba(59,130,246,0.2)]" />
        <div className="pointer-events-none absolute inset-0 -mt-[4vh] -translate-y-10 sm:-translate-y-14 lg:-translate-y-16">
          <div className="absolute left-[82%] top-[4%] h-2.5 w-2.5 rounded-full bg-sky-300/75 ring-2 ring-sky-300/20 shadow-[0_0_9px_rgba(56,189,248,0.58)]" />
          <div className="absolute left-[100%] top-[25%] h-3 w-3 -translate-x-1/2 rounded-full bg-sky-300/80 ring-2 ring-sky-300/20 shadow-[0_0_9px_rgba(56,189,248,0.58)]" />
          <div className="absolute left-[106%] top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-sky-200/90 ring-2 ring-sky-300/30 shadow-[0_0_11px_rgba(56,189,248,0.68)]" />
          <div className="absolute left-[100%] top-[75%] h-3 w-3 -translate-x-1/2 rounded-full bg-sky-300/80 ring-2 ring-sky-300/20 shadow-[0_0_9px_rgba(56,189,248,0.58)]" />
          <div className="absolute left-[82%] top-[96%] h-2.5 w-2.5 rounded-full bg-sky-300/75 ring-2 ring-sky-300/20 shadow-[0_0_9px_rgba(56,189,248,0.58)]" />
        </div>
      </div>
    </div>
  );
}
