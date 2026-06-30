import { motion } from "motion/react";

import { cn } from "../../lib/utils";
import { EegParticleCanvas } from "./EegParticleCanvas";
import {
  EEG_HOLOGRAM_VIEWBOX,
  EEG_LEAD_NODES,
  EEG_MODEL_BASE_IMAGE_SRC,
  EEG_MODEL_STAGE_ASPECT_RATIO,
  EEG_NETWORK_CURVES,
  EEG_PEDESTAL_ELLIPSES,
  cubicCurveToPath,
} from "./eegHologramGeometry";
import { resolveEegHologramTokens } from "./eegHologramTokens";
import {
  resolveDominantHeadPresentation,
  resolveEegEmotionStatusLabel,
  withAlpha,
  type EegEmotionDistributionItem,
} from "./eegEmotionPresentation";

type EegHologramPanelProps = {
  distribution: EegEmotionDistributionItem[];
  primaryLabel?: string | null;
  primaryScore?: number | null;
  deviceStatus?: string | null;
  errorMessage?: string | null;
};

function EegNetworkOverlay({
  accentColor,
  visibleCount,
  strokeWidth,
  primaryOpacity,
  secondaryOpacity,
  dashArray,
  dashDuration,
  pulseDuration,
  yOffset,
}: {
  accentColor: string;
  visibleCount: number;
  strokeWidth: number;
  primaryOpacity: number;
  secondaryOpacity: number;
  dashArray: string | null;
  dashDuration: number;
  pulseDuration: number;
  yOffset: number;
}) {
  return (
    <g transform={`translate(0 ${yOffset})`}>
      {EEG_NETWORK_CURVES.slice(0, visibleCount).map((curve, index) => {
        const opacity =
          curve.tier === "primary"
            ? primaryOpacity
            : curve.tier === "secondary"
              ? secondaryOpacity
              : secondaryOpacity * 0.92;
        const currentStrokeWidth = curve.tier === "primary" ? strokeWidth : strokeWidth - 0.18;

        return (
          <motion.path
            key={curve.key}
            d={cubicCurveToPath(curve)}
            stroke={withAlpha(accentColor, opacity)}
            strokeWidth={currentStrokeWidth}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={dashArray || undefined}
            animate={
              dashArray
                ? { opacity: [opacity * 0.58, opacity, opacity * 0.58], strokeDashoffset: [0, -16] }
                : { opacity: [opacity * 0.78, opacity, opacity * 0.78] }
            }
            transition={{
              duration: dashArray ? dashDuration : pulseDuration + index * 0.05,
              repeat: Infinity,
              ease: dashArray ? "linear" : "easeInOut",
            }}
          />
        );
      })}
    </g>
  );
}

function EegLeadNodes({
  accentColor,
  highlightColor,
  glowOpacity,
  breathDuration,
  pulseRadius,
}: {
  accentColor: string;
  highlightColor: string;
  glowOpacity: number;
  breathDuration: number;
  pulseRadius: number;
}) {
  const nodes = [
    { key: "fpz", point: EEG_LEAD_NODES.fpz, radius: 4.6, delay: 0, emphasis: 1 },
    { key: "left", point: EEG_LEAD_NODES.leftTemporal, radius: 4, delay: 0.16, emphasis: 0.86 },
    { key: "right", point: EEG_LEAD_NODES.rightTemporal, radius: 4, delay: 0.26, emphasis: 0.86 },
  ] as const;

  return (
    <>
      {nodes.map((node) => (
        <g key={node.key}>
          <motion.circle
            cx={node.point.x}
            cy={node.point.y}
            r={node.radius * 3.2}
            fill={withAlpha(accentColor, glowOpacity * 0.24 * node.emphasis)}
            animate={{
              r: [node.radius * 2.2, node.radius * 3.5 * pulseRadius, node.radius * 2.2],
              opacity: [0.18, 0.74, 0.18],
            }}
            transition={{
              duration: breathDuration,
              repeat: Infinity,
              ease: "easeInOut",
              delay: node.delay,
            }}
          />
          <motion.circle
            cx={node.point.x}
            cy={node.point.y}
            r={node.radius * 1.7}
            stroke={withAlpha(highlightColor, 0.92)}
            strokeWidth={1}
            fill="none"
            animate={{
              r: [node.radius * 1.22, node.radius * 1.95 * pulseRadius, node.radius * 1.22],
              opacity: [0.36, 1, 0.36],
            }}
            transition={{
              duration: breathDuration,
              repeat: Infinity,
              ease: "easeInOut",
              delay: node.delay,
            }}
          />
          <motion.circle
            cx={node.point.x}
            cy={node.point.y}
            r={node.radius}
            fill={withAlpha(highlightColor, 0.96)}
            animate={{ opacity: [0.64, 1, 0.64], scale: [0.92, 1.08, 0.92] }}
            transition={{
              duration: breathDuration * 0.92,
              repeat: Infinity,
              ease: "easeInOut",
              delay: node.delay,
            }}
          />
        </g>
      ))}
    </>
  );
}

function EegPedestalOverlay({
  accentColor,
  pedestalOpacity,
  pulseDuration,
}: {
  accentColor: string;
  pedestalOpacity: number;
  pulseDuration: number;
}) {
  return (
    <>
      {EEG_PEDESTAL_ELLIPSES.map((ellipse, index) => (
        <motion.ellipse
          key={`pedestal_${index}`}
          cx={160}
          cy={ellipse.cy}
          rx={ellipse.rx}
          ry={ellipse.ry}
          fill="none"
          stroke={withAlpha(accentColor, pedestalOpacity - index * 0.04)}
          strokeWidth={index === 0 ? 1.25 : 1}
          animate={{ opacity: [0.36, 0.96, 0.36], scaleX: [0.985, 1.015, 0.985], scaleY: [0.985, 1.015, 0.985] }}
          transition={{
            duration: pulseDuration + index * 0.24,
            repeat: Infinity,
            ease: "easeInOut",
            delay: index * 0.08,
          }}
          style={{ transformOrigin: "160px 400px" }}
        />
      ))}
      <motion.circle
        cx={160}
        cy={386}
        r={6}
        fill={withAlpha(accentColor, pedestalOpacity * 1.24)}
        animate={{ opacity: [0.36, 1, 0.36], r: [4.8, 7.8, 4.8] }}
        transition={{ duration: pulseDuration * 0.94, repeat: Infinity, ease: "easeInOut" }}
      />
    </>
  );
}

export function EegHologramPanel({
  distribution,
  primaryLabel,
  primaryScore,
  deviceStatus,
  errorMessage,
}: EegHologramPanelProps) {
  const presentation = resolveDominantHeadPresentation(distribution, primaryLabel, primaryScore);
  const tokens = resolveEegHologramTokens(presentation?.label);
  const hasResult = Boolean(presentation);
  const labelText = presentation?.label ?? "等待中";
  const percentageText = presentation ? `${presentation.percentage}%` : null;
  const statusText = resolveEegEmotionStatusLabel(deviceStatus, errorMessage);

  return (
    <div
      className="relative h-full overflow-hidden rounded-[22px] border border-white/10 bg-[#060b15]"
      style={{
        boxShadow: `
          inset 0 1px 0 rgba(255,255,255,0.06),
          0 18px 42px rgba(2,6,23,0.42),
          0 0 18px ${withAlpha(tokens.accentColor, tokens.haloOpacity * 0.82)}
        `,
      }}
    >
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(circle at 50% 18%, ${withAlpha(tokens.highlightColor, tokens.haloOpacity * 0.9)}, transparent 24%),
            linear-gradient(180deg, rgba(10,16,28,0.96), rgba(3,7,16,0.98))
          `,
        }}
      />
      <div
        className="absolute left-4 top-4 h-10 w-10 rounded-tl-[16px] border-l-2 border-t-2"
        style={{ borderColor: withAlpha(tokens.accentColor, hasResult ? 0.48 : 0.16) }}
      />
      <div
        className="absolute right-4 top-4 h-10 w-10 rounded-tr-[16px] border-r-2 border-t-2"
        style={{ borderColor: withAlpha(tokens.accentColor, hasResult ? 0.48 : 0.16) }}
      />

      <motion.div
        className="absolute inset-0"
        animate={{ y: tokens.bodyOffsetY }}
        transition={{ duration: 0.46, ease: "easeInOut" }}
      >
        <div
          className="absolute left-1/2 top-0 h-full -translate-x-1/2"
          style={{ aspectRatio: `${EEG_MODEL_STAGE_ASPECT_RATIO}` }}
        >
          <img
            src={EEG_MODEL_BASE_IMAGE_SRC}
            alt={`${labelText}脑电全息头模`}
            className="pointer-events-none absolute inset-0 h-full w-full object-cover"
            style={{
              filter: tokens.modelFilter,
              opacity: hasResult ? tokens.modelOpacity : 0.52,
              transform: `scale(${tokens.modelScale})`,
              transition: "filter 320ms ease, opacity 320ms ease, transform 320ms ease",
            }}
          />

          <svg
            viewBox={`0 0 ${EEG_HOLOGRAM_VIEWBOX.width} ${EEG_HOLOGRAM_VIEWBOX.height}`}
            className="pointer-events-none absolute inset-0 h-full w-full"
            fill="none"
          >
            <EegNetworkOverlay
              accentColor={tokens.accentColor}
              visibleCount={tokens.networkVisibleCount}
              strokeWidth={tokens.networkStrokeWidth}
              primaryOpacity={tokens.networkPrimaryOpacity}
              secondaryOpacity={tokens.networkSecondaryOpacity}
              dashArray={tokens.networkDashArray}
              dashDuration={tokens.networkDashShiftDuration}
              pulseDuration={tokens.networkPulseDuration}
              yOffset={tokens.networkYOffset}
            />
            <EegLeadNodes
              accentColor={tokens.accentColor}
              highlightColor={tokens.highlightColor}
              glowOpacity={tokens.nodeGlowOpacity}
              breathDuration={tokens.nodeBreathDuration}
              pulseRadius={tokens.nodePulseRadius}
            />
            <EegPedestalOverlay
              accentColor={tokens.accentColor}
              pedestalOpacity={tokens.pedestalOpacity}
              pulseDuration={tokens.pedestalPulseDuration}
            />
          </svg>

          <EegParticleCanvas accentColor={tokens.accentColor} highlightColor={tokens.highlightColor} tokens={tokens} />
        </div>
      </motion.div>

      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.02),transparent_18%,transparent_76%,rgba(255,255,255,0.02))]" />
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-[#02050c] via-[#02050c]/58 to-transparent" />

      <div className="absolute bottom-3 left-3">
        <div
          className={cn(
            "rounded-full border px-4 py-1.5 text-[12px] font-semibold tracking-[0.04em] text-slate-50 backdrop-blur-md transition-all duration-300",
            !hasResult && "text-slate-200",
          )}
          style={{
            borderColor: withAlpha(tokens.accentColor, hasResult ? 0.58 : 0.16),
            background: `linear-gradient(180deg, ${withAlpha(tokens.accentColor, hasResult ? 0.2 : 0.1)}, ${withAlpha(tokens.accentColor, hasResult ? 0.08 : 0.04)})`,
            boxShadow: `inset 0 1px 0 rgba(255,255,255,0.08), 0 0 12px ${withAlpha(tokens.accentColor, hasResult ? tokens.haloOpacity * 0.72 : 0.08)}`,
          }}
        >
          {hasResult ? labelText : statusText}
        </div>
      </div>

      {percentageText ? (
        <div
          className="absolute bottom-2 right-4 text-[42px] font-semibold tracking-[-0.06em] text-white transition-all duration-300"
          style={{
            textShadow: `
              0 0 10px ${withAlpha(tokens.highlightColor, tokens.haloOpacity * 1.1)},
              0 0 20px ${withAlpha(tokens.accentColor, tokens.haloOpacity * 1.26)}
            `,
          }}
        >
          {percentageText}
        </div>
      ) : (
        <div className="absolute bottom-3 right-3 text-[12px] font-medium text-slate-300">{statusText}</div>
      )}
    </div>
  );
}
