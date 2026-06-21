import type { ConsultationMultimodalLive, ConsultationMultimodalLivePatch } from "../types";

function buildPendingLive(): ConsultationMultimodalLive {
  return {
    speech: { status: "pending", top_3_labels: [] },
    text: { status: "pending", top_3_labels: [], negative_terms: [] },
    face: { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null },
    pose: { status: "pending", top_3_labels: [], quality_flags: {}, latest_capture_at: null },
    eeg_live: {
      status: "pending",
      device_status: "pending",
      channel_names: ["T7", "T8", "Fpz"],
      sampling_rate: 500,
      latest_results: [],
    },
    eeg_waves: {
      status: "pending",
      channel_names: ["T7", "T8", "Fpz"],
      sampling_rate: 500,
      samples: [],
      append_samples: [],
      reset: false,
    },
    updated_at: null,
  };
}

export function mergeConsultationMultimodalLive(
  current: ConsultationMultimodalLive | null | undefined,
  incoming: ConsultationMultimodalLivePatch | ConsultationMultimodalLive | null | undefined,
) {
  if (!incoming) {
    return current ?? buildPendingLive();
  }

  const base = current ?? buildPendingLive();
  const incomingEegWaves = incoming.eeg_waves;
  const shouldClearEegSamples =
    incomingEegWaves?.reset === true && incomingEegWaves?.samples === undefined;
  const baseEegWaves = base.eeg_waves ?? buildPendingLive().eeg_waves;
  const nextEegSamples = incomingEegWaves?.samples ?? (shouldClearEegSamples ? [] : baseEegWaves.samples);
  const nextEegAppendSamples =
    incomingEegWaves?.append_samples ??
    (incomingEegWaves?.samples !== undefined ? [] : baseEegWaves.append_samples);
  const nextEegReset =
    incomingEegWaves?.reset ??
    (incomingEegWaves?.samples !== undefined ? false : baseEegWaves.reset);

  return {
    ...base,
    ...incoming,
    speech: incoming.speech
      ? {
          ...base.speech,
          ...incoming.speech,
          top_3_labels: incoming.speech.top_3_labels ?? base.speech.top_3_labels,
        }
      : base.speech,
    text: incoming.text
      ? {
          ...base.text,
          ...incoming.text,
          top_3_labels: incoming.text.top_3_labels ?? base.text.top_3_labels,
          negative_terms: incoming.text.negative_terms ?? base.text.negative_terms,
        }
      : base.text,
    face: incoming.face
      ? {
          ...base.face,
          ...incoming.face,
          top_3_labels: incoming.face.top_3_labels ?? base.face.top_3_labels,
          quality_flags: incoming.face.quality_flags ?? base.face.quality_flags,
        }
      : base.face,
    pose: incoming.pose
      ? {
          ...base.pose,
          ...incoming.pose,
          top_3_labels: incoming.pose.top_3_labels ?? base.pose.top_3_labels,
          quality_flags: incoming.pose.quality_flags ?? base.pose.quality_flags,
        }
      : base.pose,
    eeg_live: incoming.eeg_live
      ? {
          ...base.eeg_live,
          ...incoming.eeg_live,
          channel_names: incoming.eeg_live.channel_names ?? base.eeg_live.channel_names,
          latest_results: incoming.eeg_live.latest_results ?? base.eeg_live.latest_results,
        }
      : base.eeg_live,
    eeg_waves: incoming.eeg_waves
      ? {
          ...base.eeg_waves,
          ...incoming.eeg_waves,
          channel_names: incoming.eeg_waves.channel_names ?? base.eeg_waves.channel_names,
          samples: nextEegSamples,
          append_samples: nextEegAppendSamples,
          reset: nextEegReset,
        }
      : base.eeg_waves,
    updated_at: incoming.updated_at ?? base.updated_at ?? null,
  };
}

export function mergeConsultationMultimodalLivePatch(
  current: ConsultationMultimodalLivePatch | null | undefined,
  incoming: ConsultationMultimodalLivePatch | null | undefined,
) {
  if (!incoming) {
    return current ?? null;
  }

  const base = current ?? {};
  const incomingEegWaves = incoming.eeg_waves;
  const shouldClearEegSamples =
    incomingEegWaves?.reset === true && incomingEegWaves?.samples === undefined;
  const baseEegWaves = base.eeg_waves;
  const nextEegSamples = incomingEegWaves?.samples ?? (shouldClearEegSamples ? [] : baseEegWaves?.samples);
  const nextEegAppendSamples =
    incomingEegWaves?.append_samples ??
    (incomingEegWaves?.samples !== undefined ? [] : baseEegWaves?.append_samples);
  const nextEegReset =
    incomingEegWaves?.reset ??
    (incomingEegWaves?.samples !== undefined ? false : baseEegWaves?.reset);

  return {
    ...base,
    ...incoming,
    speech: incoming.speech
      ? {
          ...base.speech,
          ...incoming.speech,
          top_3_labels: incoming.speech.top_3_labels ?? base.speech?.top_3_labels,
        }
      : base.speech,
    text: incoming.text
      ? {
          ...base.text,
          ...incoming.text,
          top_3_labels: incoming.text.top_3_labels ?? base.text?.top_3_labels,
          negative_terms: incoming.text.negative_terms ?? base.text?.negative_terms,
        }
      : base.text,
    face: incoming.face
      ? {
          ...base.face,
          ...incoming.face,
          top_3_labels: incoming.face.top_3_labels ?? base.face?.top_3_labels,
          quality_flags: incoming.face.quality_flags ?? base.face?.quality_flags,
        }
      : base.face,
    pose: incoming.pose
      ? {
          ...base.pose,
          ...incoming.pose,
          top_3_labels: incoming.pose.top_3_labels ?? base.pose?.top_3_labels,
          quality_flags: incoming.pose.quality_flags ?? base.pose?.quality_flags,
        }
      : base.pose,
    eeg_live: incoming.eeg_live
      ? {
          ...base.eeg_live,
          ...incoming.eeg_live,
          channel_names: incoming.eeg_live.channel_names ?? base.eeg_live?.channel_names,
          latest_results: incoming.eeg_live.latest_results ?? base.eeg_live?.latest_results,
        }
      : base.eeg_live,
    eeg_waves: incoming.eeg_waves
      ? {
          ...base.eeg_waves,
          ...incoming.eeg_waves,
          channel_names: incoming.eeg_waves.channel_names ?? base.eeg_waves?.channel_names,
          samples: nextEegSamples,
          append_samples: nextEegAppendSamples,
          reset: nextEegReset,
        }
      : base.eeg_waves,
    updated_at: incoming.updated_at ?? base.updated_at,
  };
}
