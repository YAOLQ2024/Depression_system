export type HologramPoint = {
  x: number;
  y: number;
};

export type HologramCubicCurve = {
  key: string;
  start: HologramPoint;
  control1: HologramPoint;
  control2: HologramPoint;
  end: HologramPoint;
  tier: "primary" | "secondary" | "accent";
};

export const EEG_HOLOGRAM_VIEWBOX = {
  width: 320,
  height: 480,
} as const;

export const EEG_MODEL_STAGE_ASPECT_RATIO = EEG_HOLOGRAM_VIEWBOX.width / EEG_HOLOGRAM_VIEWBOX.height;
export const EEG_MODEL_BASE_IMAGE_SRC = "/eeg-emotion/eeg-scanface-base.png";

export const EEG_LEAD_NODES = {
  fpz: { x: 160, y: 112 },
  leftTemporal: { x: 92, y: 178 },
  rightTemporal: { x: 228, y: 178 },
} as const;

function createCurve(
  key: string,
  start: HologramPoint,
  control1: HologramPoint,
  control2: HologramPoint,
  end: HologramPoint,
  tier: HologramCubicCurve["tier"],
): HologramCubicCurve {
  return { key, start, control1, control2, end, tier };
}

export const EEG_NETWORK_CURVES: HologramCubicCurve[] = [
  createCurve(
    "left_primary",
    EEG_LEAD_NODES.leftTemporal,
    { x: 112, y: 158 },
    { x: 142, y: 128 },
    EEG_LEAD_NODES.fpz,
    "primary",
  ),
  createCurve(
    "right_primary",
    EEG_LEAD_NODES.rightTemporal,
    { x: 208, y: 158 },
    { x: 178, y: 128 },
    EEG_LEAD_NODES.fpz,
    "primary",
  ),
  createCurve(
    "left_upper_primary",
    { x: 104, y: 164 },
    { x: 124, y: 130 },
    { x: 148, y: 100 },
    { x: 160, y: 88 },
    "primary",
  ),
  createCurve(
    "right_upper_primary",
    { x: 216, y: 164 },
    { x: 196, y: 130 },
    { x: 172, y: 100 },
    { x: 160, y: 88 },
    "primary",
  ),
  createCurve(
    "left_mid_secondary",
    { x: 114, y: 160 },
    { x: 132, y: 142 },
    { x: 148, y: 126 },
    { x: 160, y: 118 },
    "secondary",
  ),
  createCurve(
    "right_mid_secondary",
    { x: 206, y: 160 },
    { x: 188, y: 142 },
    { x: 172, y: 126 },
    { x: 160, y: 118 },
    "secondary",
  ),
  createCurve(
    "left_inner_accent",
    { x: 124, y: 144 },
    { x: 140, y: 128 },
    { x: 152, y: 120 },
    { x: 170, y: 118 },
    "accent",
  ),
  createCurve(
    "right_inner_accent",
    { x: 196, y: 144 },
    { x: 180, y: 128 },
    { x: 168, y: 120 },
    { x: 150, y: 118 },
    "accent",
  ),
  createCurve(
    "left_bridge_accent",
    { x: 104, y: 176 },
    { x: 128, y: 150 },
    { x: 160, y: 150 },
    { x: 194, y: 170 },
    "accent",
  ),
  createCurve(
    "right_bridge_accent",
    { x: 216, y: 176 },
    { x: 192, y: 150 },
    { x: 160, y: 150 },
    { x: 126, y: 170 },
    "accent",
  ),
];

export function cubicCurveToPath(curve: HologramCubicCurve) {
  return `M${curve.start.x} ${curve.start.y} C${curve.control1.x} ${curve.control1.y} ${curve.control2.x} ${curve.control2.y} ${curve.end.x} ${curve.end.y}`;
}

export function sampleCubicCurve(curve: HologramCubicCurve, t: number): HologramPoint {
  const clampedT = Math.min(1, Math.max(0, t));
  const inverse = 1 - clampedT;
  const x =
    inverse * inverse * inverse * curve.start.x +
    3 * inverse * inverse * clampedT * curve.control1.x +
    3 * inverse * clampedT * clampedT * curve.control2.x +
    clampedT * clampedT * clampedT * curve.end.x;
  const y =
    inverse * inverse * inverse * curve.start.y +
    3 * inverse * inverse * clampedT * curve.control1.y +
    3 * inverse * clampedT * clampedT * curve.control2.y +
    clampedT * clampedT * clampedT * curve.end.y;
  return { x, y };
}

export const EEG_BACKGROUND_COLUMNS = [
  44, 58, 74, 88, 102, 118, 134, 150, 170, 186, 202, 218, 234, 248, 264, 278,
].map((x, index) => ({
  x,
  top: 22 + (index % 4) * 8,
  bottom: 452 - (index % 3) * 14,
  weight: index % 5 === 0 ? "strong" : index % 2 === 0 ? "mid" : "soft",
}));

export const EEG_AMBIENT_POINTS: HologramPoint[] = [
  { x: 112, y: 76 },
  { x: 136, y: 68 },
  { x: 160, y: 62 },
  { x: 184, y: 68 },
  { x: 208, y: 76 },
  { x: 88, y: 112 },
  { x: 232, y: 112 },
  { x: 80, y: 154 },
  { x: 240, y: 154 },
  { x: 132, y: 316 },
  { x: 160, y: 338 },
  { x: 188, y: 316 },
  { x: 126, y: 392 },
  { x: 194, y: 392 },
];

export const EEG_PEDESTAL_ELLIPSES = [
  { rx: 68, ry: 9, cy: 384 },
  { rx: 108, ry: 18, cy: 392 },
  { rx: 146, ry: 32, cy: 404 },
];

export const EEG_CROWN_STREAM_COLUMNS = [86, 102, 118, 136, 152, 168, 184, 202, 218, 234];
export const EEG_BASE_STREAM_COLUMNS = [144, 152, 160, 168, 176];
