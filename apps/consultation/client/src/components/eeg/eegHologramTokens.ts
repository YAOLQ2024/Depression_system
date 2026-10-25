import type { EegEmotionLabel } from "./eegEmotionPresentation";

export type EegHologramState = EegEmotionLabel | "pending";

export type EegHologramTokens = {
  accentColor: string;
  highlightColor: string;
  modelFilter: string;
  modelOpacity: number;
  modelScale: number;
  meshColor: string;
  meshOpacity: number;
  contourOpacity: number;
  pointCloudOpacity: number;
  networkVisibleCount: number;
  networkStrokeWidth: number;
  networkPrimaryOpacity: number;
  networkSecondaryOpacity: number;
  networkDashArray: string | null;
  networkDashShiftDuration: number;
  networkPulseDuration: number;
  particleCount: number;
  particleSpeed: number;
  particleAlpha: number;
  ambientSparkCount: number;
  ambientSparkAlpha: number;
  streamCount: number;
  streamSpeed: number;
  streamAlpha: number;
  energyDirection: "down" | "balanced" | "up";
  networkYOffset: number;
  bodyOffsetY: number;
  nodeBreathDuration: number;
  nodePulseRadius: number;
  nodeGlowOpacity: number;
  pedestalPulseDuration: number;
  pedestalOpacity: number;
  haloOpacity: number;
  mouthLift: number;
  eyelidDrop: number;
};

const TOKENS: Record<EegHologramState, EegHologramTokens> = {
  pending: {
    accentColor: "#94a3b8",
    highlightColor: "#e2e8f0",
    modelFilter: "grayscale(0.18) saturate(0.72) brightness(0.82)",
    modelOpacity: 0.88,
    modelScale: 1,
    meshColor: "#cbd5e1",
    meshOpacity: 0.48,
    contourOpacity: 0.26,
    pointCloudOpacity: 0.18,
    networkVisibleCount: 5,
    networkStrokeWidth: 1.05,
    networkPrimaryOpacity: 0.28,
    networkSecondaryOpacity: 0.16,
    networkDashArray: "10 10",
    networkDashShiftDuration: 5.4,
    networkPulseDuration: 4.2,
    particleCount: 12,
    particleSpeed: 0.03,
    particleAlpha: 0.34,
    ambientSparkCount: 12,
    ambientSparkAlpha: 0.14,
    streamCount: 7,
    streamSpeed: 0.1,
    streamAlpha: 0.16,
    energyDirection: "balanced",
    networkYOffset: 0,
    bodyOffsetY: 0,
    nodeBreathDuration: 2.9,
    nodePulseRadius: 1,
    nodeGlowOpacity: 0.28,
    pedestalPulseDuration: 3.6,
    pedestalOpacity: 0.18,
    haloOpacity: 0.1,
    mouthLift: 0,
    eyelidDrop: 0,
  },
  消极: {
    accentColor: "#D98B79",
    highlightColor: "#F0C3B7",
    modelFilter: "hue-rotate(178deg) saturate(1.82) brightness(0.92) contrast(1.08)",
    modelOpacity: 0.98,
    modelScale: 1.004,
    meshColor: "#93c5fd",
    meshOpacity: 0.84,
    contourOpacity: 0.44,
    pointCloudOpacity: 0.2,
    networkVisibleCount: 5,
    networkStrokeWidth: 1.1,
    networkPrimaryOpacity: 0.38,
    networkSecondaryOpacity: 0.18,
    networkDashArray: "8 10",
    networkDashShiftDuration: 6.6,
    networkPulseDuration: 5.2,
    particleCount: 14,
    particleSpeed: 0.026,
    particleAlpha: 0.38,
    ambientSparkCount: 14,
    ambientSparkAlpha: 0.16,
    streamCount: 8,
    streamSpeed: 0.095,
    streamAlpha: 0.18,
    energyDirection: "down",
    networkYOffset: 9,
    bodyOffsetY: 6,
    nodeBreathDuration: 3.3,
    nodePulseRadius: 1.06,
    nodeGlowOpacity: 0.38,
    pedestalPulseDuration: 4.2,
    pedestalOpacity: 0.16,
    haloOpacity: 0.12,
    mouthLift: 5.5,
    eyelidDrop: 2.5,
  },
  中性: {
    accentColor: "#82AEE8",
    highlightColor: "#D2E3F7",
    modelFilter: "none",
    modelOpacity: 1,
    modelScale: 1.004,
    meshColor: "#fde047",
    meshOpacity: 0.9,
    contourOpacity: 0.5,
    pointCloudOpacity: 0.26,
    networkVisibleCount: 7,
    networkStrokeWidth: 1.28,
    networkPrimaryOpacity: 0.48,
    networkSecondaryOpacity: 0.24,
    networkDashArray: null,
    networkDashShiftDuration: 4.4,
    networkPulseDuration: 3.6,
    particleCount: 22,
    particleSpeed: 0.04,
    particleAlpha: 0.48,
    ambientSparkCount: 18,
    ambientSparkAlpha: 0.2,
    streamCount: 10,
    streamSpeed: 0.125,
    streamAlpha: 0.19,
    energyDirection: "balanced",
    networkYOffset: 0,
    bodyOffsetY: 0,
    nodeBreathDuration: 2.7,
    nodePulseRadius: 1.08,
    nodeGlowOpacity: 0.4,
    pedestalPulseDuration: 3.2,
    pedestalOpacity: 0.2,
    haloOpacity: 0.15,
    mouthLift: 0,
    eyelidDrop: 0.4,
  },
  积极: {
    accentColor: "#48D6B0",
    highlightColor: "#B6F2DF",
    modelFilter: "hue-rotate(78deg) saturate(1.62) brightness(0.98) contrast(1.04)",
    modelOpacity: 0.98,
    modelScale: 1.004,
    meshColor: "#86efac",
    meshOpacity: 0.96,
    contourOpacity: 0.56,
    pointCloudOpacity: 0.32,
    networkVisibleCount: 8,
    networkStrokeWidth: 1.42,
    networkPrimaryOpacity: 0.62,
    networkSecondaryOpacity: 0.34,
    networkDashArray: null,
    networkDashShiftDuration: 3.6,
    networkPulseDuration: 2.8,
    particleCount: 34,
    particleSpeed: 0.072,
    particleAlpha: 0.64,
    ambientSparkCount: 24,
    ambientSparkAlpha: 0.24,
    streamCount: 14,
    streamSpeed: 0.2,
    streamAlpha: 0.28,
    energyDirection: "up",
    networkYOffset: -5,
    bodyOffsetY: -2,
    nodeBreathDuration: 2.1,
    nodePulseRadius: 1.16,
    nodeGlowOpacity: 0.46,
    pedestalPulseDuration: 2.7,
    pedestalOpacity: 0.24,
    haloOpacity: 0.18,
    mouthLift: -4,
    eyelidDrop: -0.4,
  },
};

export function resolveEegHologramTokens(state?: EegEmotionLabel | null): EegHologramTokens {
  if (!state) {
    return TOKENS.pending;
  }
  return TOKENS[state];
}
