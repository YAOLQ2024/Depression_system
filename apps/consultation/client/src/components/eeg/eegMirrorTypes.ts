export type EegClass = 0 | 1 | 2;
export type EegGroup = "基础特征" | "PAC" | "AAC" | "PPC";
export type EegChannel = "Fpz" | "T7" | "T8";
export type EegWindowRecord = {
  sample_id: string;
  inference_id: string | null;
  turn_id: string;
  window_index: number;
  sample_started_at: string | null;
  sample_ended_at: string | null;
  prediction_status: string;
  primary_label: string | null;
  model_sha256?: string | null;
};
export type EegExplanationStatus =
  | "not_requested"
  | "queued"
  | "running"
  | "ready"
  | "failed"
  | "invalid"
  | "unavailable";
export type EegExplanationValues = {
  base_value: number;
  target_output: number;
  phi: number[];
  group_net: Record<EegGroup, number>;
  channel_net: Record<EegChannel, number>;
  channel_abs: Record<EegChannel, number>;
  channel_percent: Record<EegChannel, number> | null;
  additivity_error: number;
};
export type EegExplanation = {
  explanation_id: string;
  sample_id: string;
  inference_id: string;
  status: EegExplanationStatus;
  config_hash: string;
  config: {
    target_class: EegClass;
    model_sha256: string;
    output_kind: string;
    background_id: string | null;
  };
  sample_started_at: string | null;
  sample_ended_at: string | null;
  computed_at: string | null;
  values: EegExplanationValues | null;
  error_code: string | null;
};
export type EegHistoryItem = EegWindowRecord & {
  explanation_id: string | null;
  status: EegExplanationStatus;
  group_net: Record<EegGroup, number> | null;
  error_code: string | null;
};
export type EegHistoryPage = {
  config: EegExplanation["config"];
  config_hash: string;
  items: EegHistoryItem[];
  next_cursor: string | null;
  availability_error: string | null;
  color_scale: { min: number | null; max: number | null; unit: string };
};
