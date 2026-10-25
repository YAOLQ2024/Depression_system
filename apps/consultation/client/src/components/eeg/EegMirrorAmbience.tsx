import { useEffect, useRef } from "react";
import type { EegEmotionLabel } from "./eegEmotionPresentation";

const RATES = { 消极: 0.24, 中性: 0.65, 积极: 1.65 };

export function EegMirrorAmbience({
  label,
  color,
}: {
  label: EegEmotionLabel | null;
  color: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const state = useRef({ label, color });
  state.current = { label, color };
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    let width = 1,
      height = 1,
      frame = 0,
      last = 0,
      phase = 0,
      speed = 0.65,
      visible = true;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const resize = new ResizeObserver(([entry]) => {
      width = Math.max(1, entry.contentRect.width);
      height = Math.max(1, entry.contentRect.height);
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = width * ratio;
      canvas.height = height * ratio;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      draw(0);
    });
    const draw = (elapsed: number) => {
      const next = state.current.label ? RATES[state.current.label] : 0;
      speed += (next - speed) * Math.min(1, elapsed / 1800);
      phase += (elapsed / 1000) * speed;
      ctx.clearRect(0, 0, width, height);
      if (!state.current.label) return;
      const nodes = Array.from({ length: 48 }, (_, i) => {
        const angle = (i * Math.PI * 2) / 48;
        const radius = 1 + Math.sin(i * 2.1 + phase * 0.7) * 0.055;
        return {
          x: width * (0.5 + Math.cos(angle) * 0.44 * radius),
          y: height * (0.47 + Math.sin(angle) * 0.4 * radius),
        };
      });
      ctx.strokeStyle = state.current.color;
      ctx.fillStyle = state.current.color;
      ctx.lineWidth = 0.8;
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i],
          b = nodes[(i + (i % 3 === 0 ? 7 : 2)) % nodes.length];
        ctx.globalAlpha = 0.22;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        ctx.globalAlpha = 0.5;
        ctx.beginPath();
        ctx.arc(a.x, a.y, 1.4, 0, Math.PI * 2);
        ctx.fill();
        if (i % 2 === 0) {
          const t = (((phase * 0.12 + i * 0.173) % 1) + 1) % 1;
          ctx.globalAlpha = 0.65;
          ctx.beginPath();
          ctx.arc(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t,
            1.6,
            0,
            Math.PI * 2,
          );
          ctx.fill();
        }
      }
      // Independent feathered alpha mask: no decorative stroke crosses the face or neck.
      ctx.save();
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "destination-out";
      ctx.translate(width * 0.5, height * 0.51);
      ctx.scale(width * 0.28, height * 0.49);
      const mask = ctx.createRadialGradient(0, 0, 0.78, 0, 0, 1);
      mask.addColorStop(0, "rgba(0,0,0,1)");
      mask.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = mask;
      ctx.fillRect(-1, -1, 2, 2);
      ctx.restore();
      ctx.globalAlpha = 1;
    };
    let lastState = "";
    const tick = (now: number) => {
      frame = requestAnimationFrame(tick);
      if (document.hidden || !visible) {
        last = now;
        return;
      }
      const delta = now - last;
      if (delta < 1000 / 30) return;
      last = now;
      const key = `${state.current.label}:${state.current.color}`;
      if (!reduced.matches || key !== lastState)
        draw(reduced.matches ? 0 : Math.min(delta, 100));
      lastState = key;
    };
    const visibility = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
    });
    resize.observe(canvas);
    visibility.observe(canvas);
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect();
      visibility.disconnect();
    };
  }, []);
  return (
    <canvas
      ref={canvasRef}
      className="eeg-mirror-ambience"
      aria-hidden="true"
    />
  );
}
