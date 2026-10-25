import type {
  EegChannel,
  EegClass,
  EegExplanation,
  EegGroup,
  EegHistoryItem,
  EegHistoryPage,
  EegWindowRecord,
} from "./eegMirrorTypes";

const GROUPS: EegGroup[] = ["基础特征", "PAC", "AAC", "PPC"];
const CLASSES = ["消极", "中性", "积极"];
const REASONS: Record<string, string> = {
  queue_busy: "已有片段正在等待解释，当前片段暂未计算。请稍后重新读取。",
  background_missing: "尚未配置经验证的解释参考集。实时脑电与分类可继续使用。",
  worker_disabled: "解释计算服务尚未启用。",
  background_manifest_mismatch: "解释参考集与当前模型或处理协议不匹配。",
  background_feature_mismatch: "解释参考集的特征顺序与该预测不一致。",
  input_snapshot_missing: "这条历史预测未保存解释输入，无法追溯计算。",
  model_version_unavailable: "该片段使用的模型版本当前不可用。",
  background_version_unavailable:
    "原解释参考集已更换，无法使用新的参考集代替计算。",
  explanation_timeout: "解释计算超时，实时信号和分类不受影响。",
  additivity_check_failed: "解释数值未通过一致性校验，暂不展示。",
  prediction_replay_mismatch: "输入回放与原预测不一致，暂不展示解释。",
  unsupported_model_input: "当前模型尚未适配此解释协议。",
};
export function explanationReason(code?: string | null) {
  return code ? REASONS[code] || "该解释暂不可用，请稍后重试。" : "";
}
export function formatEegTime(value?: string | null) {
  const t = value ? new Date(value) : null;
  return t && Number.isFinite(t.getTime())
    ? t.toLocaleTimeString("zh-CN", { hour12: false })
    : "—";
}
export function formatEegInterval(
  item?: Pick<EegWindowRecord, "sample_started_at" | "sample_ended_at"> | null,
) {
  return item
    ? `${formatEegTime(item.sample_started_at)}–${formatEegTime(item.sample_ended_at)}`
    : "等待有效片段";
}
function heatColor(value: number | undefined, max: number | null) {
  if (value === undefined || !Number.isFinite(value) || !max)
    return "rgba(117,135,153,0.13)";
  const t = Math.min(1, Math.abs(value) / max);
  const zero = [75, 89, 106],
    to = value >= 0 ? [231, 183, 107] : [119, 170, 220];
  return `rgb(${zero.map((v, i) => Math.round(v + (to[i] - v) * t)).join(",")})`;
}

type Props = {
  target: EegClass;
  onTarget: (value: EegClass) => void;
  history: EegHistoryPage | null;
  detail: EegExplanation | null;
  selection: EegWindowRecord | null;
  onPin: (item: EegHistoryItem) => void;
  following: boolean;
  onFollow: () => void;
  onOlder: () => void;
  onFirstPage: () => void;
  isOlder: boolean;
  error: string;
  onRetry: () => void;
};
export function EegExplanationPanel(props: Props) {
  const { history, detail, target } = props;
  const configMatches = detail?.config_hash === history?.config_hash;
  const values =
    detail?.status === "ready" && configMatches ? detail.values : null;
  const scale = history?.color_scale.max || 1;
  const columns = [...(history?.items || [])].reverse();
  const nodes: {
    channel: EegChannel;
    x: number;
    y: number;
  }[] = [
    { channel: "Fpz", x: 150, y: 48 },
    { channel: "T7", x: 85, y: 112 },
    { channel: "T8", x: 215, y: 112 },
  ];
  const selectedOutside =
    !props.following &&
    props.selection &&
    history &&
    !history.items.some(
      (item) => item.sample_id === props.selection?.sample_id,
    );
  const pending =
    !detail || detail.status === "queued" || detail.status === "running";
  return (
    <section className="eeg-explanation" aria-label="脑电模型判断依据">
      <div className="eeg-explanation-heading">
        <div>
          <strong>{formatEegInterval(props.selection)}</strong>
          <small>
            {props.following
              ? "跟随最新片段"
              : selectedOutside
                ? "所选片段已在当前范围外 · 头像仍表示当前分类"
                : "历史片段 · 头像仍表示当前分类"}
          </small>
        </div>
        <label className="eeg-target-label">
          目标
          <select
            value={target}
            onChange={(e) => props.onTarget(Number(e.target.value) as EegClass)}
          >
            {CLASSES.map((label, i) => (
              <option key={label} value={i}>
                {label}类别
              </option>
            ))}
          </select>
        </label>
      </div>
      {(!values || props.error) && (
        <div className="eeg-explanation-feedback" aria-live="polite">
          {props.error ||
            (!props.selection?.inference_id
              ? "尚无可解释的有效分类片段，请等待信号积累。"
              : detail && !pending && !values
                ? explanationReason(detail.error_code) || "正在同步解释配置。"
                : !values && history?.availability_error
                  ? explanationReason(history.availability_error)
                  : pending
                    ? "正在读取或计算所选片段的解释…"
                    : "蓝色反对、暖金色支持所选类别的模型输出。")}
          {(props.error ||
            detail?.status === "failed" ||
            detail?.error_code === "queue_busy") && (
            <button type="button" onClick={props.onRetry}>
              重新读取
            </button>
          )}
        </div>
      )}
      <div className="eeg-explanation-top">
        <div className="eeg-explanation-card">
          <h4>三导联影响</h4>
          <div className="eeg-channel-impact">
            <svg
              className="eeg-channel-map"
              viewBox="0 0 300 170"
              role="img"
              aria-label="Fpz、T7、T8 的模型绝对影响占比"
            >
              <path
                d="M145 35 L150 28 L155 35 M82 81 Q74 30 150 34 Q226 30 218 81 Q247 149 150 157 Q53 149 82 81"
                fill="none"
                stroke="#97a6b8"
                strokeWidth="1.3"
              />
              {nodes.map(({ channel, x, y }) => {
                const percent = values?.channel_percent?.[channel];
                return (
                  <g key={channel}>
                    <title>{channel}：{percent === undefined ? "暂无数据" : `${percent}%`}</title>
                    <circle
                      cx={x}
                      cy={y}
                      r={8 + 14 * Math.sqrt((percent || 0) / 100)}
                      fill="#9cd1d8"
                      fillOpacity={percent === undefined ? 0.12 : 0.3}
                      stroke="#b6dce4"
                      strokeOpacity="0.65"
                    />
                    <circle cx={x} cy={y} r="3" fill="#b8e4ed" />
                  </g>
                );
              })}
            </svg>
            <dl className="eeg-channel-values">
              {nodes.map(({ channel }) => {
                const percent = values?.channel_percent?.[channel];
                return (
                  <div key={channel}>
                    <dt>{channel}</dt>
                    <dd>{percent === undefined ? "—" : `${percent}%`}</dd>
                  </div>
                );
              })}
            </dl>
          </div>
          <p>
            {values && !values.channel_percent
              ? "影响较小，暂不分配占比"
              : "非情绪概率"}
          </p>
        </div>
        <div className="eeg-explanation-card">
          <h4>分组净贡献</h4>
          <div className="eeg-group-bars">
            {GROUPS.map((group) => {
              const value = values?.group_net[group];
              return (
                <div className="eeg-group-row" key={group}>
                  <span>{group}</span>
                  <div className="eeg-group-track">
                    <i />
                    {value !== undefined && (
                      <b
                        style={{
                          left: value >= 0 ? "50%" : undefined,
                          right: value < 0 ? "50%" : undefined,
                          width: `${Math.min(1, Math.abs(value) / scale) * 50}%`,
                          background: value >= 0 ? "#E7B76B" : "#77AADC",
                        }}
                      />
                    )}
                  </div>
                  <strong>
                    {value === undefined
                      ? "—"
                      : `${value >= 0 ? "+" : ""}${value.toFixed(3)}`}
                  </strong>
                </div>
              );
            })}
          </div>
          <p title={`对${CLASSES[target]}类别的净贡献；组内贡献可能抵消。超出色标范围的条形截断显示。`}>
            ← 反对 · 支持 →
          </p>
        </div>
      </div>
      <div className="eeg-history-header">
        <h4 title={props.isOlder ? "历史分析窗口" : "最近 20 个分析窗口"}>{props.isOlder ? "历史窗口" : "最近窗口"}</h4>
        <div className="eeg-history-actions">
          <button type="button" onClick={props.onFollow} aria-label="回到最新片段">
            最新
          </button>
          {props.isOlder && (
            <button type="button" onClick={props.onFirstPage} aria-label="查看最近窗口">
              最近
            </button>
          )}
          <button
            type="button"
            disabled={!history?.next_cursor}
            onClick={props.onOlder}
            aria-label="查看更早窗口"
          >
            更早
          </button>
          <details className="eeg-explanation-notes">
            <summary>说明</summary>
            <p>导联数值为绝对贡献占比，并非情绪概率；影响很小时不分配占比。分组净贡献可能组内抵消，蓝色反对、暖金色支持所选类别的模型输出，超出色标范围的条形截断显示。空格表示未计算或缺失，颜色饱和表示达到色标上限。点击热图一列查看或请求该片段解释。</p>
          </details>
        </div>
      </div>
      <div className="eeg-heatmap-scroll">
        <div
          className="eeg-heatmap"
          style={{
            gridTemplateColumns: `72px repeat(${Math.max(1, columns.length)}, minmax(26px, 1fr))`,
          }}
        >
          <div className="eeg-heatmap-labels">
            {GROUPS.map((group) => (
              <span key={group}>{group}</span>
            ))}
          </div>
          {columns.length ? (
            columns.map((item) => (
              <button
                type="button"
                key={item.sample_id}
                disabled={!item.inference_id}
                aria-pressed={props.selection?.sample_id === item.sample_id}
                className="eeg-heatmap-column"
                onClick={() => props.onPin(item)}
                title={`${formatEegInterval(item)} · ${item.status === "ready" ? "解释已完成" : "解释未完成"}`}
                aria-label={`${formatEegInterval(item)}，${item.status === "ready" ? "查看解释" : "请求解释"}`}
              >
                {GROUPS.map((group) => (
                  <span
                    key={group}
                    style={{
                      background: heatColor(
                        item.group_net?.[group],
                        history?.color_scale.max || null,
                      ),
                    }}
                  >
                    {item.group_net ? "" : "·"}
                  </span>
                ))}
              </button>
            ))
          ) : (
            <div className="eeg-heatmap-empty">等待真实分析窗口</div>
          )}
        </div>
      </div>
      <div className="eeg-heatmap-footer">
        <span>
          {columns.length ? formatEegTime(columns[0].sample_started_at) : "—"}
        </span>
        <span className="eeg-color-legend">
          <i />
          {history?.color_scale.max
            ? `±${history.color_scale.max.toFixed(3)} 模型得分`
            : "色标待验证"}
        </span>
        <span>
          {columns.length
            ? formatEegTime(columns[columns.length - 1].sample_ended_at)
            : "—"}
        </span>
      </div>
    </section>
  );
}
