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
      <svg className="pointer-events-none absolute -left-[420px] top-1/2 z-0 h-[760px] w-[900px] -translate-y-1/2 overflow-visible" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        {items.map((item, index) => {
          const angle = index * STEP_ANGLE - currentAngle;
          const radians = (angle * Math.PI) / 180;
          const endX = 454 - RADIUS_X * (1 - Math.cos(radians));
          const endY = 380 + RADIUS_Y * Math.sin(radians);
          const nodeX = [35, 150, 190, 150, 35][index] || 35;
          const nodeY = [25, 178, 380, 582, 735][index] || 380;
          return <path key={`node-link-${item.id}`} d={`M ${nodeX} ${nodeY} C ${nodeX + 72} ${nodeY}, ${endX - 56} ${endY}, ${endX} ${endY}`} fill="none" stroke="rgba(125,211,252,0.34)" strokeWidth="1.2" strokeDasharray="4 6" strokeLinecap="round" />;
        })}
      </svg>
      <div className="relative z-10 flex h-full w-full items-center justify-start pl-6 sm:pl-10">
        {items.map((item, index) => {
          const angle = index * STEP_ANGLE - currentAngle;
          const radians = (angle * Math.PI) / 180;
          const orbitalX = -RADIUS_X * (1 - Math.cos(radians));
          const orbitalY = RADIUS_Y * Math.sin(radians);
          const distance = Math.abs(angle);
          const orbitStepsAway = distance / STEP_ANGLE;
          const atApex = distance < STEP_ANGLE / 2;
          const hovered = hoveredIndex === index;
          const baseScale = Math.max(0.86, 1.04 - orbitStepsAway * 0.1);
          const baseOpacity = Math.max(0.72, 1 - orbitStepsAway * 0.14);
          const blur = Math.max(0, orbitStepsAway - 1.4) * 0.2;
          const brightness = Math.max(0.86, 1 - orbitStepsAway * 0.07);
          const nearby = orbitStepsAway < 1.5;

          return (
            <motion.div
              key={item.id}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              onClick={(event) => handleItemClick(item, index, event)}
              style={{ position: "absolute", left: "-6px", top: "50%", x: orbitalX, y: orbitalY - 44, scale: hovered ? baseScale + 0.025 : baseScale, opacity: hovered ? Math.min(1, baseOpacity + 0.08) : baseOpacity, zIndex: atApex ? 40 : Math.max(10, Math.round(30 - orbitStepsAway * 8)), filter: `blur(${blur}px) brightness(${brightness})`, transformOrigin: "left center" }}
              transition={{ type: "spring", stiffness: 340, damping: 30 }}
              className="group cursor-pointer"
            >
              <div className={`relative w-[clamp(330px,22vw,450px)] overflow-visible rounded-br-[clamp(18px,1.2vw,24px)] rounded-tr-[clamp(18px,1.2vw,24px)] rounded-bl-[clamp(16px,1vw,21px)] rounded-tl-[clamp(7px,0.5vw,10px)] border px-[clamp(12px,0.9vw,18px)] py-[clamp(12px,0.8vw,16px)] shadow-sm backdrop-blur-md transition-all duration-300 ${atApex ? "border-sky-100/95 bg-[rgba(245,250,255,0.84)] shadow-[0_12px_30px_rgba(30,64,175,0.16),inset_0_1px_0_rgba(255,255,255,0.82)]" : hovered ? "border-slate-100/82 bg-[rgba(241,245,249,0.68)] shadow-md shadow-slate-900/10" : nearby ? "border-slate-100/72 bg-[rgba(226,232,240,0.58)]" : "border-slate-100/58 bg-[rgba(226,232,240,0.46)]"}`}>
                <span className={`pointer-events-none absolute -left-10 top-1/2 h-px w-10 -translate-y-1/2 ${atApex ? "bg-gradient-to-r from-sky-300/15 via-sky-400/65 to-sky-300/85 shadow-[0_0_8px_rgba(125,211,252,0.3)]" : "bg-gradient-to-r from-slate-300/10 to-slate-300/55"}`} />
                <span className={`pointer-events-none absolute -left-2 top-1/2 h-[clamp(38px,2.5vw,48px)] w-[clamp(18px,1.3vw,24px)] -translate-y-1/2 rounded-l-full border-y border-l ${atApex ? "border-sky-200/75 bg-sky-50/62" : "border-slate-100/52 bg-slate-100/30"}`} />
                {atApex && <div className="pointer-events-none absolute inset-y-3 left-0 w-[2px] rounded-r-full bg-gradient-to-b from-sky-300 via-sky-400 to-indigo-400" />}
                <div className="flex items-center justify-between gap-[clamp(10px,0.9vw,16px)]">
                  <div className="flex min-w-0 items-center gap-[clamp(10px,0.9vw,16px)]">
                    <div className={`relative -ml-[clamp(17px,1.25vw,24px)] flex h-[clamp(40px,2.5vw,50px)] w-[clamp(40px,2.5vw,50px)] shrink-0 items-center justify-center rounded-full border text-white shadow-[0_4px_10px_rgba(15,23,42,0.12)] transition-all duration-300 ${atApex ? `border-white/75 bg-gradient-to-br ${item.iconTone} ring-2 ring-white/55` : "border-slate-100/75 bg-gradient-to-br from-slate-400 to-slate-500 text-white/90 group-hover:scale-105"}`}>{item.icon}</div>
                    <div className="flex min-w-0 flex-col text-left">
                      <div className="flex items-center gap-2"><span className={`text-[clamp(15px,1.02vw,20px)] font-bold tracking-wide transition-colors ${atApex ? "text-slate-900" : "text-slate-700 group-hover:text-slate-900"}`}>{item.title}</span>{item.badge && <span className={`rounded-full border px-[clamp(7px,0.45vw,10px)] py-0.5 text-[clamp(10px,0.62vw,12px)] font-semibold ${atApex ? "border-sky-300/50 bg-sky-100/75 text-sky-700" : "border-slate-200/65 bg-slate-50/45 text-slate-500"}`}>{item.badge}</span>}</div>
                      <p className={`mt-1 truncate text-[clamp(12px,0.76vw,15px)] ${atApex ? "font-medium text-sky-700" : "text-slate-600 group-hover:text-slate-700"}`}>{item.subtitle}</p>
                    </div>
                  </div>
                  <button type="button" onClick={(event) => { event.stopPropagation(); atApex ? item.onAction() : onSelectIndex(index); }} className={`flex h-[clamp(30px,2vw,38px)] w-[clamp(30px,2vw,38px)] shrink-0 items-center justify-center rounded-full transition-all duration-200 ${atApex ? "border border-sky-200/80 bg-white/58 text-sky-700 shadow-sm hover:bg-white/86" : "border border-slate-100/45 bg-white/20 text-slate-500 group-hover:border-sky-200/65 group-hover:bg-white/46 group-hover:text-sky-700"}`} title={atApex ? `进入${item.title}` : `切换至${item.title}`}>{atApex ? <ArrowUpRight className="h-[clamp(14px,0.85vw,17px)] w-[clamp(14px,0.85vw,17px)] transition-transform group-hover:translate-x-0.5" /> : <ChevronRight className="h-[clamp(14px,0.85vw,17px)] w-[clamp(14px,0.85vw,17px)] transition-transform group-hover:translate-x-0.5" />}</button>
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
