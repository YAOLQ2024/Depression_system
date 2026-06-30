import { EegHologramPanel } from "./EegHologramPanel";
import type { EegEmotionDistributionItem } from "./eegEmotionPresentation";

type EegEmotionImagePanelProps = {
  distribution: EegEmotionDistributionItem[];
  primaryLabel?: string | null;
  primaryScore?: number | null;
  deviceStatus?: string | null;
  errorMessage?: string | null;
};

export function EegEmotionImagePanel(props: EegEmotionImagePanelProps) {
  return <EegHologramPanel {...props} />;
}
