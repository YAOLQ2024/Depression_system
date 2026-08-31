import { buildPreferredAudioConstraints } from "./mediaCapture";

export type PreparationPermissionState = PermissionState | "unsupported";

export type PreparationMediaChannelState = {
  permission: PreparationPermissionState;
  available: boolean | null;
  detectedCount: number;
  ready: boolean;
};

export type PreparationSpeakerState = {
  available: boolean | null;
  detectedCount: number;
  supported: boolean;
};

export type PreparationDeviceAccessSnapshot = {
  checked_at: string;
  capture_verified: boolean;
  secure_context: boolean;
  media_devices_supported: boolean;
  permissions_api_supported: boolean;
  browser_ready: boolean;
  camera: PreparationMediaChannelState;
  microphone: PreparationMediaChannelState;
  speaker: PreparationSpeakerState;
  all_required_ready: boolean;
};

type ProbeOptions = {
  captureVerified?: boolean;
};

function buildUnavailableSnapshot(): PreparationDeviceAccessSnapshot {
  return {
    checked_at: new Date().toISOString(),
    capture_verified: false,
    secure_context: false,
    media_devices_supported: false,
    permissions_api_supported: false,
    browser_ready: false,
    camera: { permission: "unsupported", available: null, detectedCount: 0, ready: false },
    microphone: { permission: "unsupported", available: null, detectedCount: 0, ready: false },
    speaker: { available: null, detectedCount: 0, supported: false },
    all_required_ready: false,
  };
}

async function queryPermissionState(name: "camera" | "microphone"): Promise<PreparationPermissionState> {
  if (typeof navigator === "undefined" || !navigator.permissions?.query) {
    return "unsupported";
  }

  try {
    const status = await navigator.permissions.query({ name } as PermissionDescriptor);
    return status.state;
  } catch {
    return "unsupported";
  }
}

function resolvePermissionState(
  permission: PreparationPermissionState,
  devices: MediaDeviceInfo[],
  kind: MediaDeviceKind,
  captureVerified: boolean,
): PreparationPermissionState {
  if (captureVerified) {
    return "granted";
  }

  if (permission !== "unsupported") {
    return permission;
  }

  const hasLabeledDevice = devices.some((device) => device.kind === kind && Boolean(device.label));
  return hasLabeledDevice ? "granted" : "prompt";
}

function formatCombinedAccessError(error: unknown) {
  const name = error instanceof DOMException ? error.name : error instanceof Error ? error.name : "";
  const message = error instanceof Error ? error.message : "";

  switch (name) {
    case "NotAllowedError":
    case "PermissionDeniedError":
    case "SecurityError":
      return "请在浏览器地址栏允许摄像头和麦克风访问，并确认系统隐私权限已开启。";
    case "NotFoundError":
    case "DevicesNotFoundError":
      return "未检测到可用的摄像头或麦克风设备，请检查连接状态后重试。";
    case "NotReadableError":
    case "TrackStartError":
      return "摄像头或麦克风可能正被其他应用占用，请关闭占用后重试。";
    case "OverconstrainedError":
      return "当前设备不满足浏览器采集参数要求，请切换设备后重试。";
    case "AbortError":
      return "浏览器在初始化设备时中断了请求，请稍后再试。";
    default:
      return message || "浏览器设备授权失败，请刷新页面后重试。";
  }
}

export function getPermissionStatusLabel(permission: PreparationPermissionState) {
  switch (permission) {
    case "granted":
      return "已授权";
    case "denied":
      return "已拒绝";
    case "prompt":
      return "待授权";
    default:
      return "不支持";
  }
}

export async function probePreparationDeviceAccess(
  options: ProbeOptions = {},
): Promise<PreparationDeviceAccessSnapshot> {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return buildUnavailableSnapshot();
  }

  const secureContext = window.isSecureContext;
  const mediaDevicesSupported = Boolean(navigator.mediaDevices);
  const permissionsApiSupported = Boolean(navigator.permissions?.query);

  if (!mediaDevicesSupported) {
    return {
      ...buildUnavailableSnapshot(),
      checked_at: new Date().toISOString(),
      secure_context: secureContext,
      permissions_api_supported: permissionsApiSupported,
    };
  }

  const [cameraPermissionRaw, microphonePermissionRaw] = await Promise.all([
    queryPermissionState("camera"),
    queryPermissionState("microphone"),
  ]);

  let devices: MediaDeviceInfo[] = [];
  try {
    devices = await navigator.mediaDevices.enumerateDevices();
  } catch {
    devices = [];
  }

  const captureVerified = Boolean(options.captureVerified);
  const cameraPermission = resolvePermissionState(
    cameraPermissionRaw,
    devices,
    "videoinput",
    captureVerified,
  );
  const microphonePermission = resolvePermissionState(
    microphonePermissionRaw,
    devices,
    "audioinput",
    captureVerified,
  );

  const cameraCount = devices.filter((device) => device.kind === "videoinput").length;
  const microphoneCount = devices.filter((device) => device.kind === "audioinput").length;
  const speakerCount = devices.filter((device) => device.kind === "audiooutput").length;
  const cameraAvailable = cameraCount > 0;
  const microphoneAvailable = microphoneCount > 0;
  const speakerAvailable = speakerCount > 0;
  const browserReady = secureContext && mediaDevicesSupported;

  const camera = {
    permission: cameraPermission,
    available: cameraAvailable,
    detectedCount: cameraCount,
    ready: browserReady && cameraAvailable && cameraPermission === "granted",
  };
  const microphone = {
    permission: microphonePermission,
    available: microphoneAvailable,
    detectedCount: microphoneCount,
    ready: browserReady && microphoneAvailable && microphonePermission === "granted",
  };

  return {
    checked_at: new Date().toISOString(),
    capture_verified: captureVerified,
    secure_context: secureContext,
    media_devices_supported: mediaDevicesSupported,
    permissions_api_supported: permissionsApiSupported,
    browser_ready: browserReady,
    camera,
    microphone,
    speaker: {
      available: speakerAvailable,
      detectedCount: speakerCount,
      supported: true,
    },
    all_required_ready: camera.ready && microphone.ready,
  };
}

export async function requestPreparationDeviceAccess() {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    throw new Error("当前环境不支持浏览器设备授权。");
  }

  if (!window.isSecureContext) {
    throw new Error("当前页面不是安全上下文，请使用 localhost 或 HTTPS 后再授权设备。");
  }

  if (!navigator.mediaDevices) {
    throw new Error("当前浏览器不支持摄像头/麦克风授权，请改用最新版 Chrome 或 Edge。");
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: buildPreferredAudioConstraints(),
      video: {
        facingMode: "user",
        width: { ideal: 960 },
        height: { ideal: 720 },
      },
    });

    stream.getTracks().forEach((track) => track.stop());
    return probePreparationDeviceAccess({ captureVerified: true });
  } catch (error) {
    throw new Error(formatCombinedAccessError(error));
  }
}

export function buildPreparationDeviceStatus(snapshot: PreparationDeviceAccessSnapshot | null) {
  if (!snapshot) {
    return {
      status: "unchecked",
      browser_ready: false,
    };
  }

  return {
    status: snapshot.all_required_ready ? "authorized" : "pending",
    checked_at: snapshot.checked_at,
    capture_verified: snapshot.capture_verified,
    browser_ready: snapshot.browser_ready,
    secure_context: snapshot.secure_context,
    media_devices_supported: snapshot.media_devices_supported,
    permissions_api_supported: snapshot.permissions_api_supported,
    camera: snapshot.camera,
    microphone: snapshot.microphone,
    speaker: snapshot.speaker,
  };
}
