export type MediaDeviceKind = "camera" | "microphone";

export type MediaDeviceStatusTone = "ready" | "pending" | "warning" | "error";

export type MediaDeviceFeedback = {
  title: string;
  detail: string;
  tone: MediaDeviceStatusTone;
};

function getDeviceLabel(kind: MediaDeviceKind) {
  return kind === "camera" ? "摄像头" : "麦克风";
}

export function getInitialMediaFeedback(kind: MediaDeviceKind): MediaDeviceFeedback {
  if (kind === "camera") {
    return {
      title: "正在检测摄像头",
      detail: "首次进入时会向浏览器申请摄像头权限。",
      tone: "pending",
    };
  }

  return {
    title: "麦克风待命",
    detail: "开始录音时会申请麦克风权限并检测设备。",
    tone: "pending",
  };
}

export function getUnsupportedMediaFeedback(kind: MediaDeviceKind): MediaDeviceFeedback {
  const label = getDeviceLabel(kind);
  return {
    title: `${label}不可用`,
    detail: `当前浏览器不支持${label}访问，请改用最新版 Chrome 或 Edge。`,
    tone: "error",
  };
}

export function getReadyMediaFeedback(kind: MediaDeviceKind, detail?: string): MediaDeviceFeedback {
  const label = getDeviceLabel(kind);
  return {
    title: `${label}已接入`,
    detail: detail || `${label}可正常采集。`,
    tone: "ready",
  };
}

export function getActiveMicrophoneFeedback(): MediaDeviceFeedback {
  return {
    title: "麦克风录音中",
    detail: "正在采集本轮语音并同步执行情绪分析。",
    tone: "ready",
  };
}

export function getMicrophoneCompletedFeedback(): MediaDeviceFeedback {
  return {
    title: "麦克风已授权",
    detail: "本轮录音已完成，可再次开始录音。",
    tone: "ready",
  };
}

export function describeMediaAccessError(kind: MediaDeviceKind, error: unknown): MediaDeviceFeedback {
  const label = getDeviceLabel(kind);
  const name = error instanceof DOMException ? error.name : error instanceof Error ? error.name : "";
  const message = error instanceof Error ? error.message : "";

  switch (name) {
    case "NotAllowedError":
    case "PermissionDeniedError":
    case "SecurityError":
      return {
        title: `${label}权限被拒绝`,
        detail: `请在浏览器地址栏允许${label}访问，并检查系统隐私权限是否已开启。`,
        tone: "error",
      };
    case "NotFoundError":
    case "DevicesNotFoundError":
      return {
        title: `未检测到${label}`,
        detail: `这台设备没有可用的${label}，或设备尚未正确连接。`,
        tone: "warning",
      };
    case "NotReadableError":
    case "TrackStartError":
      return {
        title: `${label}暂时不可用`,
        detail: `${label}可能正被其他应用占用，或被系统隐私设置阻止访问。`,
        tone: "warning",
      };
    case "OverconstrainedError":
      return {
        title: `${label}参数不兼容`,
        detail: `当前设备不满足采集参数要求，请切换设备或调整浏览器权限后重试。`,
        tone: "warning",
      };
    case "AbortError":
      return {
        title: `${label}启动被中断`,
        detail: `浏览器在初始化${label}时中断了请求，请稍后重试。`,
        tone: "warning",
      };
    default:
      if (message.includes("Requested device not found")) {
        return {
          title: `未检测到${label}`,
          detail: `浏览器没有找到可用的${label}设备，请检查设备连接或系统设置。`,
          tone: "warning",
        };
      }
      return {
        title: `${label}接入失败`,
        detail: message || `${label}初始化失败，请刷新页面后重试。`,
        tone: "error",
      };
  }
}
