import { useCallback, useEffect, useRef, useState, type MouseEvent, type PointerEvent, type ReactNode, type WheelEvent } from "react";
import { ArrowUpRight, ChevronRight, Clock } from "lucide-react";
import { motion } from "motion/react";

export type HomeOrbitalMenuItem = {
  id: string;
  title: string;
  subtitle: string;
  badge?: string;
  estimatedTime: string;
  iconTone: string;
  icon: ReactNode;
  onAction: () => void;
};

type HomeOrbitalMenuProps = {
  items: HomeOrbitalMenuItem[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
};

// These are intentionally the same geometry values as the supplied reference page.
const STEP_ANGLE = 26;
const RADIUS_X = 260;
const RADIUS_Y = 380;

export function HomeOrbitalMenu({ items, selectedIndex, onSelectIndex }: HomeOrbitalMenuProps) {
  const [targetAngle, setTargetAngle] = useState(selectedIndex * STEP_ANGLE);
  const [currentAngle, setCurrentAngle] = useState(selectedIndex * STEP_ANGLE);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartY, setDragStartY] = useState(0);
  const [dragStartAngle, setDragStartAngle] = useState(0);
  const [dragVelocity, setDragVelocity] = useState(0);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const lastDragYRef = useRef(0);
  const lastDragTimeRef = useRef(0);
  const lastWheelTimeRef = useRef(0);

  useEffect(() => setTargetAngle(selectedIndex * STEP_ANGLE), [selectedIndex]);

  useEffect(() => {
    let animationFrameId = 0;
    const updatePhysics = () => {
      setCurrentAngle((previous) => {
        const difference = targetAngle - previous;
        return Math.abs(difference) < 0.05 ? targetAngle : previous + difference * 0.14;
      });
      animationFrameId = requestAnimationFrame(updatePhysics);
    };
    animationFrameId = requestAnimationFrame(updatePhysics);
    return () => cancelAnimationFrame(animationFrameId);
  }, [targetAngle]);

  const snapToClosestIndex = useCallback(
    (angle: number) => {
      const nextIndex = Math.max(0, Math.min(items.length - 1, Math.round(angle / STEP_ANGLE)));
      setTargetAngle(nextIndex * STEP_ANGLE);
      if (nextIndex !== selectedIndex) onSelectIndex(nextIndex);
    },
    [items.length, onSelectIndex, selectedIndex],
  );

  const handleWheel = useCallback(
    (event: WheelEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      const now = Date.now();
      if (now - lastWheelTimeRef.current < 160 || Math.abs(event.deltaY) < 15) return;
      lastWheelTimeRef.current = now;
      const nextIndex = event.deltaY > 0 ? Math.min(items.length - 1, selectedIndex + 1) : Math.max(0, selectedIndex - 1);
      if (nextIndex !== selectedIndex) {
        setTargetAngle(nextIndex * STEP_ANGLE);
        onSelectIndex(nextIndex);
      }
    },
    [items.length, onSelectIndex, selectedIndex],
  );

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    setIsDragging(true);
    setDragStartY(event.clientY);
    setDragStartAngle(currentAngle);
    lastDragYRef.current = event.clientY;
    lastDragTimeRef.current = Date.now();
    setDragVelocity(0);
    (event.target as HTMLElement).setPointerCapture?.(event.pointerId);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    const now = Date.now();
    const currentY = event.clientY;
    const nextAngle = dragStartAngle - (currentY - dragStartY) / 4.5;
    const boundedAngle = Math.max(-10, Math.min((items.length - 1) * STEP_ANGLE + 10, nextAngle));
    const elapsed = Math.max(1, now - lastDragTimeRef.current);
    setDragVelocity(((currentY - lastDragYRef.current) / elapsed) * 15);
    lastDragYRef.current = currentY;
    lastDragTimeRef.current = now;
    setCurrentAngle(boundedAngle);
    setTargetAngle(boundedAngle);
  };

  const handlePointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    setIsDragging(false);
    try {
      (event.target as HTMLElement).releasePointerCapture?.(event.pointerId);
    } catch {
      // Pointer capture may have been released by the browser already.
    }
    snapToClosestIndex(currentAngle - dragVelocity * 0.4);
  };

  const handleItemClick = (item: HomeOrbitalMenuItem, index: number, event: MouseEvent) => {
    event.stopPropagation();
    if (index === selectedIndex) item.onAction();
    else {
      setTargetAngle(index * STEP_ANGLE);
      onSelectIndex(index);
    }
  };

  return (
    <div
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      className={`pointer-events-auto relative flex h-full min-h-[640px] w-full select-none items-center justify-start touch-none ${isDragging ? "cursor-grabbing" : "cursor-grab"}`}
    >
      <svg className="pointer-events-none absolute -left-28 top-1/2 z-0 h-[760px] w-[580px] -translate-y-1/2 overflow-visible" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
          <linearGradient id="home-orbit-arc" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(14,165,233,0.3)" />
            <stop offset="40%" stopColor="rgba(14,165,233,0.7)" />
            <stop offset="50%" stopColor="rgba(59,130,246,0.9)" />
            <stop offset="60%" stopColor="rgba(14,165,233,0.7)" />
            <stop offset="100%" stopColor="rgba(99,102,241,0.3)" />
          </linearGradient>
          <linearGradient id="home-active-beam" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(2,132,199,0.96)" />
            <stop offset="60%" stopColor="rgba(79,70,229,0.8)" />
            <stop offset="100%" stopColor="rgba(14,165,233,0.85)" />
          </linearGradient>
          <linearGradient id="home-passive-beam" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(2,132,199,1)" />
            <stop offset="60%" stopColor="rgba(79,70,229,0.9)" />
            <stop offset="100%" stopColor="rgba(14,165,233,0.82)" />
          </linearGradient>
          <filter id="home-soft-glow"><feGaussianBlur stdDeviation="2.5" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <path d="M 50 60 C 220 180, 260 380, 260 380 C 260 380, 220 580, 50 700" fill="none" stroke="url(#home-orbit-arc)" strokeWidth="2.6" strokeDasharray="7 7" opacity="1" />
        {items.map((item, index) => {
          const angle = index * STEP_ANGLE - currentAngle;
          const radians = (angle * Math.PI) / 180;
          const endX = 220 - RADIUS_X * (1 - Math.cos(radians));
          const endY = 380 + RADIUS_Y * Math.sin(radians);
          const startY = 380 + angle * 3.6;
          const atApex = Math.abs(angle) < STEP_ANGLE / 2;
          return (
            <g key={`orbit-beam-${item.id}`}>
              <path d={`M 50 ${startY} C 100 ${startY}, ${endX - 60} ${endY}, ${endX} ${endY}`} fill="none" stroke={atApex ? "url(#home-active-beam)" : "url(#home-passive-beam)"} strokeWidth={atApex ? 3.6 : 3} strokeDasharray={atApex ? "none" : "8 5"} strokeLinecap="round" filter="url(#home-soft-glow)" opacity={Math.max(0.84, 1 - Math.abs(angle) / 150)} />
              <circle cx={endX} cy={endY} r={atApex ? 5 : 3.5} fill={atApex ? "#0ea5e9" : "#60a5fa"} stroke="rgba(255,255,255,0.95)" strokeWidth="1.5" filter={atApex ? "url(#home-soft-glow)" : undefined} opacity={Math.max(0.76, 1 - Math.abs(angle) / 100)} />
            </g>
          );
        })}
        <line x1="200" y1="380" x2="250" y2="380" stroke="rgba(14,165,233,0.76)" strokeWidth="1.8" strokeDasharray="4 4" />
        <circle cx="250" cy="380" r="3.5" fill="#38bdf8" />
      </svg>

      <div className="relative z-10 flex h-full w-full items-center justify-start pl-6 sm:pl-10">
        {items.map((item, index) => {
          const angle = index * STEP_ANGLE - currentAngle;
          const radians = (angle * Math.PI) / 180;
          const orbitalX = -RADIUS_X * (1 - Math.cos(radians));
          const orbitalY = RADIUS_Y * Math.sin(radians);
          const distance = Math.abs(angle);
          const atApex = distance < STEP_ANGLE / 2;
          const hovered = hoveredIndex === index;
          const baseScale = Math.max(0.84, 1.1 - (distance / 110) * 0.28);
          const baseOpacity = Math.max(0.45, 1 - (distance / 90) * 0.58);
          const blur = distance > 35 ? (distance - 35) * 0.03 : 0;

          return (
            <motion.div
              key={item.id}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              onClick={(event) => handleItemClick(item, index, event)}
              style={{ position: "absolute", left: "50px", top: "50%", x: orbitalX, y: orbitalY - 44, scale: hovered ? baseScale + 0.04 : baseScale, opacity: hovered ? Math.min(1, baseOpacity + 0.25) : baseOpacity, zIndex: atApex ? 40 : Math.max(10, Math.round(30 - distance)), filter: blur ? `blur(${blur}px)` : "none", transformOrigin: "left center" }}
              transition={{ type: "spring", stiffness: 340, damping: 30 }}
              className="group cursor-pointer"
            >
              <div className={`relative w-[340px] overflow-hidden rounded-[20px] border p-3.5 shadow-lg backdrop-blur-xl transition-all duration-300 sm:w-[380px] sm:p-4 lg:w-[410px] ${atApex ? "border-sky-400 bg-[linear-gradient(112deg,rgba(255,255,255,0.96),rgba(224,242,254,0.92)_54%,rgba(238,242,255,0.96))] shadow-[0_16px_42px_rgba(37,99,235,0.28),0_0_30px_rgba(56,189,248,0.28)] ring-2 ring-white/70" : hovered ? "border-sky-300/80 bg-white/88 shadow-xl shadow-sky-900/15" : "border-white/80 bg-white/62 shadow-[0_10px_28px_rgba(15,23,42,0.12)]"}`}>
                <div className={`pointer-events-none absolute inset-y-0 left-0 w-1 transition-all ${atApex ? "bg-gradient-to-b from-sky-300 via-sky-500 to-indigo-500" : "bg-sky-300/55"}`} />
                <div className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full bg-sky-300/20 blur-2xl" />
                {atApex && <><div className="absolute inset-y-2 left-0 w-[4px] rounded-r-full bg-gradient-to-b from-sky-300 via-sky-500 to-indigo-500 shadow-[0_0_12px_#38bdf8]" /><div className="absolute left-8 right-8 top-0 h-[2px] bg-gradient-to-r from-transparent via-sky-400 to-transparent" /></>}
                <div className="flex items-center justify-between gap-3.5">
                  <div className="flex min-w-0 items-center gap-3.5">
                    <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/80 bg-gradient-to-br text-white shadow-[0_5px_14px_rgba(15,23,42,0.18)] transition-all duration-300 ${item.iconTone} ${atApex ? "scale-105 ring-2 ring-white/70" : "group-hover:scale-105"}`}>{item.icon}</div>
                    <div className="flex min-w-0 flex-col text-left">
                      <div className="flex items-center gap-2"><span className={`text-sm font-bold tracking-wide transition-colors sm:text-base ${atApex ? "text-slate-900" : "text-slate-700 group-hover:text-slate-900"}`}>{item.title}</span>{item.badge && <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${atApex ? "border-sky-400/40 bg-sky-100 text-sky-700" : "border-slate-200/90 bg-white/75 text-slate-500"}`}>{item.badge}</span>}</div>
                      <p className={`mt-1 truncate text-xs ${atApex ? "font-medium text-sky-700" : "text-slate-500 group-hover:text-slate-600"}`}>{item.subtitle}</p>
                    </div>
                  </div>
                  <button type="button" onClick={(event) => { event.stopPropagation(); atApex ? item.onAction() : onSelectIndex(index); }} className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition-all duration-200 ${atApex ? "bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-[0_7px_16px_rgba(37,99,235,0.34)] hover:scale-105" : "border border-white/90 bg-white/78 text-slate-500 shadow-sm group-hover:border-sky-300 group-hover:bg-sky-50 group-hover:text-sky-700"}`} title={atApex ? `进入${item.title}` : `切换至${item.title}`}>{atApex ? <ArrowUpRight className="h-4 w-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" /> : <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />}</button>
                </div>
                {atApex && <div className="mt-2.5 flex items-center border-t border-sky-400/30 pt-2 text-[11px] font-medium text-sky-700"><span className="flex items-center gap-1"><Clock className="h-3 w-3" />{item.estimatedTime}</span></div>}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
