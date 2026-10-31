import { useEffect, useId, useMemo, useRef, useState } from "react";
import type {
  EegLivePayload,
  EegWavePreview as WavePayload,
  EegWaveSample,
} from "../../types";
import { EegHologramPanel } from "./EegHologramPanel";
import { EegWavePreview } from "./EegWavePreview";
import {
  EegExplanationPanel,
  formatEegInterval,
  formatEegTime,
} from "./EegExplanationPanel";
import {
  getEegEmotionConfig,
  normalizeEegEmotionDistribution,
} from "./eegEmotionPresentation";
import { useEegMirrorData } from "./useEegMirrorData";
import { buildEegTimeline } from "./eegMirrorTimeline";
import type { EegClass } from "./eegMirrorTypes";
import "./eegMirror.css";

const EMPTY_SAMPLES: EegWaveSample[] = [];

export function EegMirrorPanel({
  sessionId,
  live,
  waves,
  explanationUpdate,
}: {
  explanationUpdate?: string;
  sessionId?: string | null;
  live: EegLivePayload;
  waves: WavePayload;
}) {
  const [mode, setMode] = useState<"eeg" | "explanation">("eeg");
  const [target, setTarget] = useState<EegClass>(2);
  const [now, setNow] = useState(Date.now);
  const viewId = useId();
  const rate = waves.sampling_rate || 256;
  // Keep the live buffer and mounted wave plots independent of the selected view.
  const buffer = useRef<{
    full: EegWaveSample[] | undefined;
    append: EegWaveSample[] | undefined;
    reset: boolean;
    samples: EegWaveSample[];
  }>({ full: undefined, append: undefined, reset: false, samples: [] });
  const cache = buffer.current;
  if (cache.full !== waves.samples || (waves.reset && !cache.reset)) {
    cache.samples = [...(waves.samples || EMPTY_SAMPLES)];
    cache.full = waves.samples;
    cache.append = undefined;
  }
  if (cache.append !== waves.append_samples) {
    const last = cache.samples[cache.samples.length - 1];
    const lastAt = Date.parse(last?.captured_at || "");
    const added = (waves.append_samples || EMPTY_SAMPLES).filter((s) => {
      const at = Date.parse(s.captured_at || "");
      return !Number.isFinite(lastAt) || !Number.isFinite(at) || at >= lastAt;
    });
    const overlap = last
      ? added.findIndex(
          (s) => s.seq === last.seq && s.captured_at === last.captured_at,
        )
      : -1;
    cache.samples = [...cache.samples, ...added.slice(overlap + 1)].slice(
      -Math.ceil(rate * 4 + 1),
    );
    cache.append = waves.append_samples;
  }
  cache.reset = Boolean(waves.reset);
  const fullSamples = useMemo(
    () => buffer.current.samples,
    [waves.samples, waves.reset],
  );
  const latest = live.latest_result;
  const data = useEegMirrorData(
    sessionId,
    latest?.inference_id,
    target,
    mode === "explanation",
    explanationUpdate,
  );
  const latestSample = cache.samples[cache.samples.length - 1];
  const signalAt = Date.parse(
    latestSample?.captured_at || live.updated_at || "",
  );
  const hasSignal = Number.isFinite(signalAt);
  const signalStale = hasSignal && now - signalAt > 4000;
  const started = Date.parse(latest?.sample_started_at || ""),
    ended = Date.parse(latest?.sample_ended_at || "");
  const resultStale =
    !Number.isFinite(ended) ||
    now - ended > Math.max(20000, (ended - started) * 3 || 0);
  const disconnected = [
    "disabled",
    "idle",
    "disconnected",
    "dependency_missing",
  ].includes(live.device_status || "");
  const calibrating = live.calibration?.required && live.calibration.status !== "ready";
  const stale = calibrating || !hasSignal || signalStale || resultStale || disconnected;
  const status = disconnected
    ? "设备未连接"
    : !hasSignal
      ? "等待信号"
      : signalStale
        ? "信号暂未更新"
        : "正在接收信号";
  const timeline = useMemo(
    () => buildEegTimeline(data.windows, now),
    [data.windows, now],
  );
  const distribution = useMemo(
    () => normalizeEegEmotionDistribution(latest?.top_3_labels),
    [latest?.top_3_labels],
  );
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    setMode("eeg");
  }, [sessionId]);
  return (
    <div className="eeg-mirror">
      <header className="eeg-mirror-header">
        <h3>脑电情绪镜像</h3>
        <div className="eeg-mirror-tabs" role="tablist" aria-label="脑电数据视图">
          <button
            type="button"
            role="tab"
            id={`${viewId}-live-tab`}
            aria-controls={`${viewId}-live-panel`}
            aria-selected={mode === "eeg"}
            onClick={() => setMode("eeg")}
          >
            实时 EEG
          </button>
          <button
            type="button"
            role="tab"
            id={`${viewId}-basis-tab`}
            aria-controls={`${viewId}-basis-panel`}
            aria-selected={mode === "explanation"}
            onClick={() => {
              data.follow();
              setMode("explanation");
            }}
          >
            判断依据
          </button>
        </div>
        <div
          className="eeg-mirror-connection"
          title={`最近信号 ${formatEegTime(latestSample?.captured_at || live.updated_at)}`}
        >
          <span
            className={`eeg-mirror-dot ${!hasSignal || signalStale || disconnected ? "is-stale" : ""}`}
          />
          {status}
        </div>
      </header>
      <div className="eeg-mirror-main">
        <section className="eeg-mirror-face" aria-label="当前情绪映像">
          <div className="eeg-mirror-face-title">
            情绪映像{" "}
            <small>
              {stale && latest?.primary_label ? "上次有效结果" : "当前分类"}
            </small>
          </div>
          <EegHologramPanel
            distribution={distribution}
            primaryLabel={latest?.primary_label}
            inactive={stale}
            deviceStatus={live.device_status}
            errorMessage={live.error_message}
          />
          <div className="eeg-mirror-result-time">
            {calibrating
              ? `正在校准 ${live.calibration!.collected_frames}/${live.calibration!.target_frames} 帧，完成后开始分类`
              : latest?.primary_label
              ? formatEegInterval({
                  sample_started_at: latest.sample_started_at || null,
                  sample_ended_at: latest.sample_ended_at || null,
                })
              : "等待足够的有效片段"}
          </div>
        </section>
        <section className="eeg-mirror-signal" aria-label="信号与判断依据">
          <div
            className="eeg-mirror-waves"
            role="tabpanel"
            id={`${viewId}-live-panel`}
            aria-labelledby={`${viewId}-live-tab`}
            hidden={mode !== "eeg"}
          >
            {cache.samples.length ? (
              <EegWavePreview
                samples={fullSamples}
                appendSamples={waves.append_samples || EMPTY_SAMPLES}
                reset={Boolean(waves.reset)}
                channelNames={
                  waves.channel_names ||
                  live.channel_names || ["T7", "T8", "Fpz"]
                }
                samplingRate={rate}
              />
            ) : (
              <div className="eeg-mirror-waiting">
                请佩戴脑电设备，按问诊提示开始回答。
                <small>收到真实信号后显示波形</small>
              </div>
            )}
            <div className="eeg-mirror-wave-caption">
              采集 {live.sampling_rate || "—"} Hz · 预览 {rate} Hz · 最近 4 秒
              {signalStale ? " · 停止新增" : ""}
            </div>
          </div>
          <div
            role="tabpanel"
            id={`${viewId}-basis-panel`}
            aria-labelledby={`${viewId}-basis-tab`}
            hidden={mode !== "explanation"}
          >
            {mode === "explanation" && (
              <EegExplanationPanel
                target={target}
                onTarget={(value) => {
                  data.resetTarget();
                  setTarget(value);
                }}
                history={data.history}
                detail={data.detail}
                selection={data.selection}
                onPin={data.pin}
                following={data.following}
                onFollow={data.follow}
                onOlder={data.older}
                onFirstPage={data.firstPage}
                isOlder={data.isOlder}
                error={data.error}
                onRetry={data.retry}
              />
            )}
          </div>
        </section>
      </div>
      <footer className="eeg-mirror-footer">
        <div className="eeg-mirror-record-title">
          <strong>近期记录</strong>
          <span>
            {timeline.majority === "记录积累中" ||
            timeline.majority === "近期状态多变"
              ? timeline.majority
              : `近期以${timeline.majority}为主`}
          </span>
          <small>
            最近 60 秒 · 有效覆盖 {(timeline.coverageMs / 1000).toFixed(0)} 秒
          </small>
        </div>
        <div
          className="eeg-mirror-timeline"
          role="img"
          aria-label="最近60秒分类记录，灰色为未识别或缺失"
        >
          {timeline.segments.map((s, i) => (
            <span
              key={i}
              style={{
                flex: s.end - s.start,
                background: s.label
                  ? getEegEmotionConfig(s.label).accentColor
                  : "#596778",
              }}
              title={`${formatEegTime(new Date(s.start).toISOString())}–${formatEegTime(new Date(s.end).toISOString())} ${s.label || "未识别或缺失"}`}
            />
          ))}
        </div>
        <div className="eeg-mirror-record-legend">
          <span>分类只覆盖有效分析片段</span>
          <span>
            中性 <i style={{ background: "#82AEE8" }} />
            积极 <i style={{ background: "#48D6B0" }} />
            消极 <i style={{ background: "#D98B79" }} />
          </span>
        </div>
        {live.error_message && (
          <div className="eeg-mirror-error" role="status">
            脑电识别暂不可用，请检查设备连接。
          </div>
        )}
      </footer>
    </div>
  );
}
