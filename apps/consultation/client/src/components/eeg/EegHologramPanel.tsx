import { useEffect, type CSSProperties } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  coerceEegEmotionLabel,
  getDefaultEegEmotionConfig,
  getEegEmotionConfig,
  resolveEegEmotionStatusLabel,
  type EegEmotionDistributionItem,
} from "./eegEmotionPresentation";
import { EegMirrorAmbience } from "./EegMirrorAmbience";

type Props = {
  distribution: EegEmotionDistributionItem[];
  primaryLabel?: string | null;
  primaryScore?: number | null;
  deviceStatus?: string | null;
  errorMessage?: string | null;
  inactive?: boolean;
};

export function EegHologramPanel({
  primaryLabel,
  deviceStatus,
  errorMessage,
  inactive = false,
}: Props) {
  const label = coerceEegEmotionLabel(primaryLabel);
  const config = label
    ? getEegEmotionConfig(label)
    : getDefaultEegEmotionConfig();
  const reduced = useReducedMotion();
  useEffect(() => {
    for (const emotion of ["消极", "中性", "积极"] as const) {
      const image = new Image();
      image.src = getEegEmotionConfig(emotion).imageSrc;
    }
  }, []);
  return (
    <div
      className="eeg-mirror-avatar"
      style={{ "--emotion-color": config.accentColor } as CSSProperties}
    >
      <div className="eeg-mirror-avatar-halo" />
      <EegMirrorAmbience
        label={inactive ? null : label}
        color={config.accentColor}
      />
      <AnimatePresence initial={false}>
        <motion.img
          key={label || "pending"}
          src={config.imageSrc}
          alt={label ? `${label}情绪映像` : "等待脑电识别的情绪映像"}
          className="eeg-mirror-head"
          initial={{ opacity: 0 }}
          animate={{ opacity: label ? 0.64 : 0.28 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduced ? 0 : 1.8, ease: "easeInOut" }}
          style={{
            filter: label
              ? inactive
                ? "saturate(.45)"
                : "none"
              : "grayscale(1)",
          }}
          draggable={false}
        />
      </AnimatePresence>
      <div className="eeg-mirror-avatar-caption">
        <span className="eeg-mirror-dot" />
        {label || resolveEegEmotionStatusLabel(deviceStatus, errorMessage)}
      </div>
    </div>
  );
}
