import { motion, useDragControls } from "motion/react";

interface DraggableMessagePanelProps {
  message: string;
  title?: string;
}

export function DraggableMessagePanel({ message, title = "AI 数字人医生" }: DraggableMessagePanelProps) {
  const dragControls = useDragControls();

  return (
    <motion.div 
      drag
      dragControls={dragControls}
      dragListener={false}
      dragMomentum={false}
      style={{ x: 0, y: 0 }}
      className="w-[240px] sm:w-[280px] min-w-[200px] min-h-[120px] max-w-[80vw] max-h-[80vh] resize bg-slate-900/10 backdrop-blur-md border border-indigo-400/60 rounded-3xl p-[clamp(16px,4cqw,20px)] shadow-[0_0_30px_rgba(99,102,241,0.6),inset_0_0_15px_rgba(165,180,252,0.4)] flex flex-col pointer-events-auto relative overflow-hidden ring-1 ring-indigo-400/30 text-left touch-none"
    >
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-indigo-400/10 to-transparent pointer-events-none"></div>
      
      {/* Drag Handle Area */}
      <div className="relative z-10 flex flex-col h-full pointer-events-none">
        <div 
           className="cursor-grab active:cursor-grabbing pointer-events-auto pb-2 -mt-2 pt-2"
           onPointerDown={(e) => dragControls.start(e)}
        >
          <p className="text-white/80 text-xs font-bold tracking-widest flex items-center gap-2 shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-400 shadow-[0_0_8px_rgba(96,165,250,0.8)] animate-[pulse_2s_ease-in-out_infinite]"></span>
            {title}
          </p>
        </div>
        <div className="flex-1 overflow-y-auto w-full pointer-events-auto scrollbar-thin scrollbar-track-transparent scrollbar-thumb-white/20 pr-2 mask-image-b pb-2 text-wrap break-words">
          <p className="text-slate-100 text-[13px] md:text-sm leading-relaxed tracking-wide min-h-[60px] drop-shadow-sm pointer-events-auto cursor-text whitespace-pre-wrap">
            {message}
          </p>
        </div>
      </div>
    </motion.div>
  );
}
