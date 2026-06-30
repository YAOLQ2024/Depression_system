import { useEffect, useMemo, useRef } from "react";

import {
  EEG_AMBIENT_POINTS,
  EEG_BACKGROUND_COLUMNS,
  EEG_BASE_STREAM_COLUMNS,
  EEG_CROWN_STREAM_COLUMNS,
  EEG_HOLOGRAM_VIEWBOX,
  EEG_NETWORK_CURVES,
  sampleCubicCurve,
  type HologramCubicCurve,
  type HologramPoint,
} from "./eegHologramGeometry";
import type { EegHologramTokens } from "./eegHologramTokens";

type EegParticleCanvasProps = {
  accentColor: string;
  highlightColor: string;
  tokens: EegHologramTokens;
};

type NetworkParticle = {
  curve: HologramCubicCurve;
  phase: number;
  radius: number;
  alpha: number;
  speedFactor: number;
  direction: 1 | -1;
};

type AmbientSpark = {
  point: HologramPoint;
  phase: number;
  radius: number;
  alpha: number;
};

type StreamParticle = {
  x: number;
  phase: number;
  radius: number;
  alpha: number;
  section: "crown" | "base";
  reverse: boolean;
};

function mulberry32(seed: number) {
  let current = seed >>> 0;
  return function next() {
    current |= 0;
    current = (current + 0x6d2b79f5) | 0;
    let hash = Math.imul(current ^ (current >>> 15), 1 | current);
    hash = (hash + Math.imul(hash ^ (hash >>> 7), 61 | hash)) ^ hash;
    return ((hash ^ (hash >>> 14)) >>> 0) / 4294967296;
  };
}

function resizeCanvasToDisplaySize(canvas: HTMLCanvasElement) {
  const devicePixelRatio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width * devicePixelRatio));
  const height = Math.max(1, Math.round(rect.height * devicePixelRatio));

  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  return {
    devicePixelRatio,
    width: canvas.width / devicePixelRatio,
    height: canvas.height / devicePixelRatio,
  };
}

function withAlpha(hexColor: string, alpha: number) {
  const normalized = hexColor.replace("#", "");
  if (normalized.length !== 6) {
    return hexColor;
  }
  const red = Number.parseInt(normalized.slice(0, 2), 16);
  const green = Number.parseInt(normalized.slice(2, 4), 16);
  const blue = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${Math.min(1, Math.max(0, alpha))})`;
}

function lerp(start: number, end: number, ratio: number) {
  return start + (end - start) * ratio;
}

function fract(value: number) {
  return value - Math.floor(value);
}

function drawGlowCircle(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  color: string,
  alpha: number,
) {
  const gradient = context.createRadialGradient(x, y, 0, x, y, radius);
  gradient.addColorStop(0, withAlpha(color, alpha));
  gradient.addColorStop(0.4, withAlpha(color, alpha * 0.52));
  gradient.addColorStop(1, withAlpha(color, 0));

  context.fillStyle = gradient;
  context.beginPath();
  context.arc(x, y, radius, 0, Math.PI * 2);
  context.fill();
}

function createNetworkParticles(tokens: EegHologramTokens) {
  const curves = EEG_NETWORK_CURVES.slice(0, tokens.networkVisibleCount);
  const random = mulberry32(tokens.particleCount * 97 + tokens.networkVisibleCount * 17);

  return Array.from({ length: Math.max(1, tokens.particleCount) }, (_, index) => {
    const curve = curves[index % curves.length];
    const direction =
      tokens.energyDirection === "up"
        ? -1
        : tokens.energyDirection === "balanced"
          ? index % 2 === 0
            ? 1
            : -1
          : 1;

    return {
      curve,
      phase: random(),
      radius: 0.9 + random() * 1.65,
      alpha: 0.55 + random() * 0.45,
      speedFactor: 0.76 + random() * 0.72,
      direction: direction as 1 | -1,
    };
  });
}

function createAmbientSparks(tokens: EegHologramTokens) {
  const random = mulberry32(tokens.ambientSparkCount * 83 + tokens.networkVisibleCount * 29);
  const points = [...EEG_AMBIENT_POINTS];
  const sparks: AmbientSpark[] = [];

  for (let index = 0; index < tokens.ambientSparkCount; index += 1) {
    const point = points[Math.floor(random() * points.length)];
    sparks.push({
      point,
      phase: random() * Math.PI * 2,
      radius: 0.7 + random() * 1.2,
      alpha: 0.45 + random() * 0.55,
    });
  }

  return sparks;
}

function createStreamParticles(tokens: EegHologramTokens) {
  const random = mulberry32(tokens.streamCount * 71 + tokens.particleCount * 13);
  const columns =
    tokens.streamCount > EEG_CROWN_STREAM_COLUMNS.length
      ? [...EEG_CROWN_STREAM_COLUMNS, ...EEG_BASE_STREAM_COLUMNS]
      : EEG_CROWN_STREAM_COLUMNS;
  const particles: StreamParticle[] = [];

  for (let index = 0; index < tokens.streamCount; index += 1) {
    const section = index % 3 === 0 ? "base" : "crown";
    const source = section === "base" ? EEG_BASE_STREAM_COLUMNS : columns;
    const x = source[Math.floor(random() * source.length)];

    particles.push({
      x,
      section,
      phase: random(),
      radius: 0.9 + random() * 1.5,
      alpha: 0.38 + random() * 0.5,
      reverse:
        tokens.energyDirection === "up"
          ? true
          : tokens.energyDirection === "balanced"
            ? index % 2 === 0
            : false,
    });
  }

  return particles;
}

function pointToCanvas(point: HologramPoint, width: number, height: number) {
  return {
    x: (point.x / EEG_HOLOGRAM_VIEWBOX.width) * width,
    y: (point.y / EEG_HOLOGRAM_VIEWBOX.height) * height,
  };
}

export function EegParticleCanvas({ accentColor, highlightColor, tokens }: EegParticleCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const startAtRef = useRef<number | null>(null);

  const networkParticles = useMemo(() => createNetworkParticles(tokens), [tokens]);
  const ambientSparks = useMemo(() => createAmbientSparks(tokens), [tokens]);
  const streamParticles = useMemo(() => createStreamParticles(tokens), [tokens]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return undefined;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return undefined;
    }

    const drawFrame = (timestamp: number) => {
      if (startAtRef.current === null) {
        startAtRef.current = timestamp;
      }
      const elapsed = (timestamp - startAtRef.current) / 1000;
      const { devicePixelRatio, width, height } = resizeCanvasToDisplaySize(canvas);

      context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      context.clearRect(0, 0, width, height);
      context.globalCompositeOperation = "screen";

      for (const column of EEG_BACKGROUND_COLUMNS) {
        const x = (column.x / EEG_HOLOGRAM_VIEWBOX.width) * width;
        const top = (column.top / EEG_HOLOGRAM_VIEWBOX.height) * height;
        const bottom = (column.bottom / EEG_HOLOGRAM_VIEWBOX.height) * height;
        const alpha =
          column.weight === "strong" ? tokens.streamAlpha * 0.34 : column.weight === "mid" ? tokens.streamAlpha * 0.22 : tokens.streamAlpha * 0.14;
        context.strokeStyle = withAlpha(accentColor, alpha);
        context.lineWidth = column.weight === "strong" ? 1 : 0.7;
        context.beginPath();
        context.moveTo(x, top);
        context.lineTo(x, bottom);
        context.stroke();
      }

      for (const spark of ambientSparks) {
        const point = pointToCanvas(spark.point, width, height);
        const pulse = 0.5 + 0.5 * Math.sin(elapsed * 1.8 + spark.phase);
        drawGlowCircle(
          context,
          point.x,
          point.y,
          spark.radius * (0.9 + pulse * 0.7),
          highlightColor,
          tokens.ambientSparkAlpha * spark.alpha * (0.28 + pulse * 0.72),
        );
      }

      for (const particle of networkParticles) {
        const cycle = fract(elapsed * tokens.particleSpeed * particle.speedFactor + particle.phase);
        const progress = particle.direction === 1 ? cycle : 1 - cycle;
        const point = pointToCanvas(sampleCubicCurve(particle.curve, progress), width, height);
        const trailStep =
          tokens.energyDirection === "up" ? 0.082 : tokens.energyDirection === "balanced" ? 0.062 : 0.044;
        const previousProgress =
          particle.direction === 1 ? Math.max(0, progress - trailStep) : Math.min(1, progress + trailStep);
        const previousPoint = pointToCanvas(sampleCubicCurve(particle.curve, previousProgress), width, height);
        const yOffset = tokens.networkYOffset * Math.sin(progress * Math.PI);
        const alpha = tokens.particleAlpha * particle.alpha;

        context.strokeStyle = withAlpha(accentColor, alpha * 0.45);
        context.lineWidth = particle.radius * 0.92;
        context.beginPath();
        context.moveTo(previousPoint.x, previousPoint.y + yOffset);
        context.lineTo(point.x, point.y + yOffset);
        context.stroke();

        drawGlowCircle(
          context,
          point.x,
          point.y + yOffset,
          particle.radius * (tokens.energyDirection === "up" ? 7.2 : 6.1),
          highlightColor,
          alpha * 0.34,
        );

        context.fillStyle = withAlpha(highlightColor, alpha * 0.95);
        context.beginPath();
        context.arc(point.x, point.y + yOffset, particle.radius, 0, Math.PI * 2);
        context.fill();
      }

      for (const particle of streamParticles) {
        const cycle =
          tokens.energyDirection === "balanced"
            ? 0.5 - 0.5 * Math.cos((elapsed * tokens.streamSpeed + particle.phase) * Math.PI * 2)
            : fract(elapsed * tokens.streamSpeed + particle.phase);
        const startY = particle.section === "crown" ? 46 : 308;
        const endY = particle.section === "crown" ? 164 : 424;
        const progress = particle.reverse ? 1 - cycle : cycle;
        const y = lerp(startY, endY, progress);
        const canvasX = (particle.x / EEG_HOLOGRAM_VIEWBOX.width) * width;
        const canvasY = (y / EEG_HOLOGRAM_VIEWBOX.height) * height;
        const trailLength = particle.section === "crown" ? 24 : 32;
        const directionMultiplier = particle.reverse ? -1 : 1;

        context.strokeStyle = withAlpha(accentColor, tokens.streamAlpha * particle.alpha * 0.55);
        context.lineWidth = 1.05;
        context.beginPath();
        context.moveTo(canvasX, canvasY - trailLength * directionMultiplier);
        context.lineTo(canvasX, canvasY + 3 * directionMultiplier);
        context.stroke();

        drawGlowCircle(
          context,
          canvasX,
          canvasY,
          particle.radius * 4.2,
          accentColor,
          tokens.streamAlpha * particle.alpha * 0.28,
        );

        context.fillStyle = withAlpha(highlightColor, tokens.streamAlpha * particle.alpha * 0.95);
        context.beginPath();
        context.arc(canvasX, canvasY, particle.radius, 0, Math.PI * 2);
        context.fill();
      }

      animationFrameRef.current = window.requestAnimationFrame(drawFrame);
    };

    animationFrameRef.current = window.requestAnimationFrame(drawFrame);
    const handleResize = () => {
      if (!canvasRef.current) {
        return;
      }
      resizeCanvasToDisplaySize(canvasRef.current);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      startAtRef.current = null;
      if (animationFrameRef.current !== null) {
        window.cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [accentColor, ambientSparks, highlightColor, networkParticles, streamParticles, tokens]);

  return <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full" />;
}
