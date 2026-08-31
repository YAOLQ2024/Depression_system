type AudioDebugEntry = {
  ts: string;
  scope: string;
  detail?: unknown;
};

declare global {
  interface Window {
    __mcsAudioDebug?: AudioDebugEntry[];
  }
}

const MAX_AUDIO_DEBUG_ENTRIES = 200;

export function logAudioDebug(scope: string, detail?: unknown) {
  const entry: AudioDebugEntry = {
    ts: new Date().toISOString(),
    scope,
    detail,
  };

  if (typeof window !== "undefined") {
    const nextEntries = [...(window.__mcsAudioDebug || []), entry];
    if (nextEntries.length > MAX_AUDIO_DEBUG_ENTRIES) {
      nextEntries.splice(0, nextEntries.length - MAX_AUDIO_DEBUG_ENTRIES);
    }
    window.__mcsAudioDebug = nextEntries;
  }

  if (typeof console !== "undefined") {
    console.info(`[mcs-audio] ${scope}`, detail ?? "");
  }
}
