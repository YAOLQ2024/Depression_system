import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  Camera,
  Check,
  Edit3,
  Mic,
  MonitorPlay,
  Ruler,
  ShieldAlert,
  User,
  Volume2,
  Weight,
  X,
} from "lucide-react";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { AppToast } from "../components/AppToast";
import {
  buildPreparationDeviceStatus,
  getPermissionStatusLabel,
  probePreparationDeviceAccess,
  requestPreparationDeviceAccess,
  type PreparationDeviceAccessSnapshot,
} from "../lib/preparationDeviceAccess";
import { ConsultationLayout } from "../layouts";
import { useTimedToast } from "../lib/useTimedToast";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import type { UpdateUserProfilePayload } from "../services/api/contracts";

type PreparationFormData = {
  full_name: string;
  age: string;
  gender: string;
  height_cm: string;
  weight_kg: string;
  marital_status: string;
  parents_marital_status: string;
  parents_occupation: string;
  prior_psychiatric_visit: string;
};

const EMPTY_PROFILE: PreparationFormData = {
  full_name: "",
  age: "",
  gender: "",
  height_cm: "",
  weight_kg: "",
  marital_status: "",
  parents_marital_status: "",
  parents_occupation: "",
  prior_psychiatric_visit: "",
};

const GENDER_OPTIONS = ["男", "女", "其他", "不愿透露"];
const MARITAL_STATUS_OPTIONS = ["未婚", "已婚", "离异", "丧偶", "其他"];
const PARENTS_MARITAL_STATUS_OPTIONS = ["已婚", "离异", "分居", "一方离世", "其他"];
const PRIOR_PSYCHIATRIC_VISIT_OPTIONS = ["否", "是", "不确定"];

function getDisplayValue(value: string) {
  return value || "未填写";
}

function stringifyNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "" : String(value);
}

function buildFormDataFromUser(
  user: {
    full_name: string;
    profile?: {
      gender?: string | null;
      age?: number | null;
      height_cm?: number | null;
      weight_kg?: number | null;
      marital_status?: string | null;
      parents_marital_status?: string | null;
      parents_occupation?: string | null;
      prior_psychiatric_visit?: string | null;
    } | null;
  } | null,
): PreparationFormData {
  if (!user) {
    return { ...EMPTY_PROFILE };
  }

  return {
    full_name: user.full_name || "",
    age: stringifyNumber(user.profile?.age),
    gender: user.profile?.gender || "",
    height_cm: stringifyNumber(user.profile?.height_cm),
    weight_kg: stringifyNumber(user.profile?.weight_kg),
    marital_status: user.profile?.marital_status || "",
    parents_marital_status: user.profile?.parents_marital_status || "",
    parents_occupation: user.profile?.parents_occupation || "",
    prior_psychiatric_visit: user.profile?.prior_psychiatric_visit || "",
  };
}

function buildProfilePayload(formData: PreparationFormData): UpdateUserProfilePayload {
  const payload: UpdateUserProfilePayload = {
    full_name: formData.full_name.trim(),
  };

  if (formData.gender.trim()) {
    payload.gender = formData.gender.trim();
  }

  if (formData.marital_status.trim()) {
    payload.marital_status = formData.marital_status.trim();
  }

  if (formData.parents_marital_status.trim()) {
    payload.parents_marital_status = formData.parents_marital_status.trim();
  }

  if (formData.parents_occupation.trim()) {
    payload.parents_occupation = formData.parents_occupation.trim();
  }

  if (formData.prior_psychiatric_visit.trim()) {
    payload.prior_psychiatric_visit = formData.prior_psychiatric_visit.trim();
  }

  return payload;
}

function validateAndBuildProfilePayload(
  formData: PreparationFormData,
): { payload: UpdateUserProfilePayload | null; error: string | null } {
  const payload: UpdateUserProfilePayload = {
    full_name: formData.full_name.trim(),
  };

  const ageText = formData.age.trim();
  if (ageText) {
    const age = Number(ageText);
    if (!Number.isInteger(age) || age < 0 || age > 120) {
      return { payload: null, error: "年龄需填写 0 到 120 之间的整数。" };
    }
    payload.age = age;
  }

  const heightText = formData.height_cm.trim();
  if (heightText) {
    const height = Number(heightText);
    if (!Number.isFinite(height) || height < 0) {
      return { payload: null, error: "身高需填写大于等于 0 的数字。" };
    }
    payload.height_cm = height;
  }

  const weightText = formData.weight_kg.trim();
  if (weightText) {
    const weight = Number(weightText);
    if (!Number.isFinite(weight) || weight < 0) {
      return { payload: null, error: "体重需填写大于等于 0 的数字。" };
    }
    payload.weight_kg = weight;
  }

  return {
    payload: {
      ...buildProfilePayload(formData),
      ...payload,
    },
    error: null,
  };
}

type DeviceIndicatorTone = "ready" | "pending" | "warning" | "error";

function getChannelIndicator(
  channel: PreparationDeviceAccessSnapshot["camera"] | PreparationDeviceAccessSnapshot["microphone"] | null,
): { text: string; tone: DeviceIndicatorTone } {
  if (!channel) {
    return { text: "待检测", tone: "pending" };
  }

  if (channel.ready) {
    return { text: "已授权", tone: "ready" };
  }

  if (channel.available === false) {
    return { text: "未检测", tone: "warning" };
  }

  if (channel.permission === "denied") {
    return { text: "已拒绝", tone: "error" };
  }

  if (channel.permission === "unsupported") {
    return { text: "不支持", tone: "error" };
  }

  return { text: getPermissionStatusLabel(channel.permission), tone: "pending" };
}

function getSpeakerIndicator(snapshot: PreparationDeviceAccessSnapshot | null): { text: string; tone: DeviceIndicatorTone } {
  if (!snapshot) {
    return { text: "待检测", tone: "pending" };
  }

  if (snapshot.speaker.available) {
    return { text: "已检测", tone: "ready" };
  }

  return { text: "未检测", tone: "warning" };
}

function getBrowserIndicator(snapshot: PreparationDeviceAccessSnapshot | null): { text: string; tone: DeviceIndicatorTone } {
  if (!snapshot) {
    return { text: "待检测", tone: "pending" };
  }

  if (snapshot.browser_ready) {
    return { text: "已就绪", tone: "ready" };
  }

  if (!snapshot.secure_context) {
    return { text: "需 HTTPS", tone: "error" };
  }

  if (!snapshot.media_devices_supported) {
    return { text: "不支持", tone: "error" };
  }

  return { text: "未就绪", tone: "warning" };
}

function formatCheckedAt(timestamp: string | null | undefined) {
  if (!timestamp) {
    return "";
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleString("zh-CN", {
    hour12: false,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function PreparationPage() {
  const { state, actions } = useConsultationAppContext();
  const navigate = useNavigate();
  const { toast, pushToast } = useTimedToast();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deviceAccess, setDeviceAccess] = useState<PreparationDeviceAccessSnapshot | null>(null);
  const [isCheckingDevices, setIsCheckingDevices] = useState(false);
  const [dataConsentConfirmedAt, setDataConsentConfirmedAt] = useState<string | null>(null);
  const [selectedDoctorPersonaId, setSelectedDoctorPersonaId] = useState<string | null>(null);
  const [doctorSelectedAt, setDoctorSelectedAt] = useState<string | null>(null);
  const [formData, setFormData] = useState<PreparationFormData>(EMPTY_PROFILE);
  const [formError, setFormError] = useState("");

  const profile = buildFormDataFromUser(state.user);
  const savedPreparationState = state.user?.preparation_state || null;
  const doctorPersonas = state.bootstrap?.doctor_personas || [];
  const selectedDoctorPersona =
    doctorPersonas.find((persona) => persona.persona_id === selectedDoctorPersonaId) || null;
  const displayedDoctorPersona = selectedDoctorPersona || doctorPersonas[0] || null;
  const hasSavedProfile = Boolean(profile.full_name.trim());
  const isDeviceAuth = Boolean(deviceAccess?.all_required_ready);
  const isDataAuth = Boolean(dataConsentConfirmedAt);
  const isDoctorSelected = Boolean(selectedDoctorPersonaId);
  const isReady = hasSavedProfile && isDeviceAuth && isDataAuth && isDoctorSelected;
  const readyCount = [hasSavedProfile, isDeviceAuth, isDataAuth, isDoctorSelected].filter(Boolean).length;
  const resumableConsultationId =
    state.consultation && state.consultation.status !== "handoff_ready"
      ? state.consultation.session_id
      : null;
  const cameraIndicator = getChannelIndicator(deviceAccess?.camera || null);
  const microphoneIndicator = getChannelIndicator(deviceAccess?.microphone || null);
  const speakerIndicator = getSpeakerIndicator(deviceAccess);
  const browserIndicator = getBrowserIndicator(deviceAccess);
  const deviceSummaryText = deviceAccess?.all_required_ready
    ? "摄像头和麦克风已完成真实授权，开始问诊时会把本次设备状态同步到后端会话。"
    : "请先完成浏览器摄像头与麦克风授权；页面也会同步检测扬声器和浏览器环境。";
  const deviceCheckedAtText = formatCheckedAt(
    deviceAccess?.checked_at || ((savedPreparationState?.device_status as Record<string, unknown> | undefined)?.checked_at as string | undefined),
  );
  const doctorSelectedAtText = formatCheckedAt(doctorSelectedAt);

  useEffect(() => {
    if (state.message) {
      pushToast(state.message, "success");
      actions.resetFeedback();
    }
  }, [actions, pushToast, state.message]);

  useEffect(() => {
    if (state.error) {
      pushToast(state.error, "error");
      actions.resetFeedback();
    }
  }, [actions, pushToast, state.error]);

  useEffect(() => {
    setDataConsentConfirmedAt(
      savedPreparationState?.consent_confirmed
        ? savedPreparationState.consent_confirmed_at || new Date().toISOString()
        : null,
    );
    setSelectedDoctorPersonaId(savedPreparationState?.assigned_doctor_persona || null);
    setDoctorSelectedAt(savedPreparationState?.doctor_selected_at || null);
  }, [
    savedPreparationState?.assigned_doctor_persona,
    savedPreparationState?.consent_confirmed,
    savedPreparationState?.consent_confirmed_at,
    savedPreparationState?.doctor_selected_at,
    state.user?.id,
  ]);

  useEffect(() => {
    let cancelled = false;

    async function refreshDeviceAccess() {
      const snapshot = await probePreparationDeviceAccess();
      if (!cancelled) {
        setDeviceAccess(snapshot);
      }
    }

    void refreshDeviceAccess();

    const mediaDevices = typeof navigator !== "undefined" ? navigator.mediaDevices : null;
    const handleDeviceChange = () => {
      void refreshDeviceAccess();
    };

    mediaDevices?.addEventListener?.("devicechange", handleDeviceChange);
    window.addEventListener("focus", handleDeviceChange);

    return () => {
      cancelled = true;
      mediaDevices?.removeEventListener?.("devicechange", handleDeviceChange);
      window.removeEventListener("focus", handleDeviceChange);
    };
  }, []);

  const openProfileModal = () => {
    actions.resetFeedback();
    setFormError("");
    setFormData(profile);
    setIsModalOpen(true);
  };

  const handleSaveProfile = async () => {
    const normalizedFullName = formData.full_name.trim();
    if (!normalizedFullName) {
      setFormError("姓名不能为空。");
      return;
    }

    const { payload, error } = validateAndBuildProfilePayload(formData);
    if (!payload) {
      setFormError(error || "表单信息校验失败。");
      return;
    }

    setFormError("");
    const updatedUser = await actions.savePreparationProfile(payload);
    if (updatedUser) {
      setFormData(buildFormDataFromUser(updatedUser));
      setIsModalOpen(false);
    }
  };

  const persistPreparationState = async ({
    deviceStatus = deviceAccess ? buildPreparationDeviceStatus(deviceAccess) : undefined,
    consentConfirmed = isDataAuth,
    consentConfirmedAt = dataConsentConfirmedAt,
    assignedDoctorPersona = selectedDoctorPersonaId,
    doctorPickedAt = doctorSelectedAt,
  }: {
    deviceStatus?: Record<string, unknown>;
    consentConfirmed?: boolean;
    consentConfirmedAt?: string | null;
    assignedDoctorPersona?: string | null;
    doctorPickedAt?: string | null;
  } = {}) => {
    return actions.savePreparationState({
      ...(deviceStatus ? { device_status: deviceStatus } : {}),
      consent_confirmed: consentConfirmed,
      consent_confirmed_at: consentConfirmedAt,
      assigned_doctor_persona: assignedDoctorPersona,
      doctor_selected_at: doctorPickedAt,
    });
  };

  const handleAuthorizeDevices = async () => {
    actions.resetFeedback();
    setIsCheckingDevices(true);

    try {
      const snapshot = await requestPreparationDeviceAccess();
      setDeviceAccess(snapshot);
      await persistPreparationState({
        deviceStatus: buildPreparationDeviceStatus(snapshot),
      });
      if (snapshot.all_required_ready) {
        pushToast("摄像头与麦克风已完成授权。", "success");
      } else {
        pushToast("设备状态已更新，但仍有设备未就绪，请检查后重试。", "error");
      }
    } catch (caught) {
      pushToast(caught instanceof Error ? caught.message : "浏览器设备授权失败，请重试。", "error");
      const snapshot = await probePreparationDeviceAccess();
      setDeviceAccess(snapshot);
    } finally {
      setIsCheckingDevices(false);
    }
  };

  const handleConfirmDataConsent = async () => {
    if (isDataAuth) {
      return;
    }

    const previousConfirmedAt = dataConsentConfirmedAt;
    const confirmedAt = new Date().toISOString();
    setDataConsentConfirmedAt(confirmedAt);
    try {
      await persistPreparationState({
        consentConfirmed: true,
        consentConfirmedAt: confirmedAt,
      });
      pushToast("已记录本次数据采集同意，开始问诊时会同步写入会话。", "success");
    } catch (caught) {
      setDataConsentConfirmedAt(previousConfirmedAt);
      pushToast(caught instanceof Error ? caught.message : "保存数据采集同意状态失败，请重试。", "error");
    }
  };

  const handleSelectDoctorPersona = async () => {
    if (!doctorPersonas.length) {
      pushToast("医生风格仍在加载，请稍后再试。", "error");
      return;
    }

    const currentIndex = doctorPersonas.findIndex((persona) => persona.persona_id === selectedDoctorPersonaId);
    const nextPersona = currentIndex >= 0 ? doctorPersonas[(currentIndex + 1) % doctorPersonas.length] : doctorPersonas[0];
    const previousDoctorPersonaId = selectedDoctorPersonaId;
    const previousDoctorSelectedAt = doctorSelectedAt;
    const selectedAt = new Date().toISOString();

    setSelectedDoctorPersonaId(nextPersona.persona_id);
    setDoctorSelectedAt(selectedAt);
    try {
      await persistPreparationState({
        assignedDoctorPersona: nextPersona.persona_id,
        doctorPickedAt: selectedAt,
      });
      pushToast(`已选择 ${nextPersona.display_name}。`, "success");
    } catch (caught) {
      setSelectedDoctorPersonaId(previousDoctorPersonaId);
      setDoctorSelectedAt(previousDoctorSelectedAt);
      pushToast(caught instanceof Error ? caught.message : "保存医生选择失败，请重试。", "error");
    }
  };

  const handleStartConsultation = async () => {
    if (!isReady) return;
    if (resumableConsultationId) {
      navigate(APP_PATHS.consultation, { state: { sessionId: resumableConsultationId } });
      return;
    }
    const started = await actions.handleStartConsultation({
      device_status: buildPreparationDeviceStatus(deviceAccess),
      audio_channel_ready: Boolean(
        deviceAccess?.browser_ready &&
          deviceAccess?.microphone.ready &&
          (deviceAccess?.speaker.available ?? true),
      ),
      consent_confirmed: isDataAuth,
      consultation_ready_state: isReady ? "ready" : "pending_preparation",
      assigned_doctor_persona: selectedDoctorPersonaId,
    });
    if (started) {
      navigate(APP_PATHS.consultation, { state: { sessionId: started.session_id } });
    }
  };

  return (
    <ConsultationLayout backgroundImage="/4K.png" title="问诊准备">
      <AppToast toast={toast} />
      <div className="w-full h-full px-4 pt-2 pb-4 md:px-8 md:pt-2 md:pb-2 flex flex-col items-center z-10 text-white font-sans overflow-y-auto">
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-4 md:gap-6 mt-0">
          <div className="bg-[linear-gradient(135deg,rgba(255,255,255,0.42),rgba(226,232,240,0.30))] border border-white/55 rounded-[2rem] p-6 shadow-2xl relative overflow-hidden flex flex-col text-slate-900 [backdrop-filter:blur(28px)_saturate(135%)]">
            <div className="absolute top-0 right-0 p-8 opacity-20 pointer-events-none">
              <svg
                width="120"
                height="120"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z" />
                <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z" />
                <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4" />
                <path d="M17.599 6.5a3 3 0 0 0 .399-1.375" />
                <path d="M6.002 6.5A3 3 0 0 1 5.602 5.125" />
                <path d="M11.8 21.2a1.2 1.2 0 0 0-1.183-1.18" />
                <path d="M13.383 20.02a1.2 1.2 0 0 0-1.183 1.18" />
              </svg>
            </div>

            <h2 className="text-3xl font-bold tracking-wider mb-2 z-10">信息录入</h2>
            <p className="text-slate-700 text-sm mb-6 z-10">
              {hasSavedProfile
                ? "以下为您当前账号已保存的个人信息，请确认是否准确，如有错误可继续修改。"
                : "请先填写您的基础信息，以便我们为您提供更准确的评估。"}
            </p>

            {hasSavedProfile ? (
              <div className="grid grid-cols-2 gap-3 z-10">
                <InfoCard icon={<User className="w-5 h-5 text-blue-300" />} label="姓名" value={getDisplayValue(profile.full_name)} className="col-span-2" />
                <InfoCard icon={<span className="text-xl leading-none text-blue-300">♂</span>} label="性别" value={getDisplayValue(profile.gender)} />
                <InfoCard icon={<span className="text-xl leading-none text-blue-300">📅</span>} label="年龄" value={getDisplayValue(profile.age)} />
                <InfoCard icon={<Ruler className="w-5 h-5 text-blue-300" />} label="身高" value={profile.height_cm ? `${profile.height_cm} cm` : "未填写"} />
                <InfoCard icon={<Weight className="w-5 h-5 text-blue-300" />} label="体重" value={profile.weight_kg ? `${profile.weight_kg} kg` : "未填写"} />
                <InfoCard icon={<span className="text-base text-blue-300">婚</span>} label="婚姻状态" value={getDisplayValue(profile.marital_status)} />
                <InfoCard icon={<span className="text-base text-blue-300">家</span>} label="父母婚姻状态" value={getDisplayValue(profile.parents_marital_status)} />
                <InfoCard icon={<span className="text-base text-blue-300">业</span>} label="父母职业" value={getDisplayValue(profile.parents_occupation)} className="col-span-2" />
                <InfoCard icon={<span className="text-base text-blue-300">♡</span>} label="既往精神/心理就诊" value={getDisplayValue(profile.prior_psychiatric_visit)} className="col-span-2" />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center min-h-[300px] border-2 border-dashed border-white/55 rounded-2xl bg-white/28 z-10">
                <p className="text-slate-600 text-sm">当前账号暂未填写信息</p>
              </div>
            )}

            <button
              onClick={openProfileModal}
              className="mt-6 w-full py-4 rounded-full bg-gradient-to-r from-blue-500/35 to-purple-500/35 border border-white/50 hover:from-blue-500/45 hover:to-purple-500/45 transition-colors shadow-[0_0_15px_rgba(255,255,255,0.1)] flex items-center justify-center gap-2 group z-10"
            >
              <Edit3 className="w-5 h-5 group-hover:scale-110 transition-transform" />
              <span className="font-medium tracking-wide">{hasSavedProfile ? "修改信息" : "填写信息"}</span>
            </button>
          </div>

          <div className="flex flex-col gap-4">
            <div className="bg-[linear-gradient(135deg,rgba(255,255,255,0.38),rgba(226,232,240,0.28))] border border-white/50 rounded-3xl p-6 relative overflow-hidden flex flex-col sm:flex-row gap-6 sm:items-center text-slate-900 [backdrop-filter:blur(28px)_saturate(135%)]">
              <div className="text-4xl font-bold text-blue-400 opacity-60 absolute top-4 left-4">01</div>
              <div className="flex-1 pl-12">
                <div className="flex w-full justify-between items-center mb-1">
                  <h3 className="text-xl font-bold">设备与采集授权</h3>
                  <StatusBadge isDone={isDeviceAuth} textDone="已授权" textPending="待授权" />
                </div>
                <p className="text-slate-700 text-sm mb-4">{deviceSummaryText}</p>
                <div className="flex gap-4 sm:gap-8 justify-start">
                  <DeviceIcon icon={<Camera />} label="摄像头" statusText={cameraIndicator.text} tone={cameraIndicator.tone} />
                  <DeviceIcon icon={<Mic />} label="麦克风" statusText={microphoneIndicator.text} tone={microphoneIndicator.tone} />
                  <DeviceIcon icon={<Volume2 />} label="扬声器" statusText={speakerIndicator.text} tone={speakerIndicator.tone} />
                  <DeviceIcon icon={<MonitorPlay />} label="浏览器环境" statusText={browserIndicator.text} tone={browserIndicator.tone} />
                </div>
                {deviceCheckedAtText ? (
                  <p className="text-xs text-slate-600 mt-4">最近检测：{deviceCheckedAtText}</p>
                ) : null}
              </div>
              <div className="flex-shrink-0 mt-4 sm:mt-0">
                <button
                  onClick={handleAuthorizeDevices}
                  disabled={isCheckingDevices}
                  className={cn(
                    "px-8 py-3 rounded-full font-medium transition-all",
                    isCheckingDevices
                      ? "bg-white/35 text-slate-500 border border-white/45"
                      : "bg-gradient-to-r from-purple-500 to-blue-600 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)]",
                  )}
                >
                  {isCheckingDevices ? "检测中..." : isDeviceAuth ? "重新检测" : "立即授权"}
                </button>
              </div>
            </div>

            <div className="bg-[linear-gradient(135deg,rgba(255,255,255,0.38),rgba(226,232,240,0.28))] border border-white/50 rounded-3xl p-6 relative overflow-hidden flex flex-col sm:flex-row gap-6 sm:items-center text-slate-900 [backdrop-filter:blur(28px)_saturate(135%)]">
              <div className="text-4xl font-bold text-blue-400 opacity-60 absolute top-4 left-4">02</div>
              <div className="flex-1 pl-12">
                <div className="flex w-full justify-between items-center mb-1">
                  <h3 className="text-xl font-bold">数据采集说明与授权</h3>
                  <StatusBadge isDone={isDataAuth} textDone="已确认" textPending="待确认" />
                </div>
                <p className="text-slate-700 text-sm mb-4">本次问诊将采集多维度数据用于辅助评估，开始问诊时会把本次同意状态写入会话。</p>
                <div className="flex items-center gap-2 text-sm text-blue-200 bg-blue-500/10 w-fit px-3 py-1.5 rounded-full cursor-pointer hover:bg-blue-500/20 transition-colors">
                  <ShieldAlert className="w-4 h-4" />
                  <span>已阅读并同意本次数据采集说明</span>
                  <span className="text-blue-400 ml-2">查看详情 →</span>
                </div>
                {dataConsentConfirmedAt ? (
                  <p className="text-xs text-slate-600 mt-4">确认时间：{formatCheckedAt(dataConsentConfirmedAt)}</p>
                ) : null}
              </div>
              <div className="flex-shrink-0 mt-4 sm:mt-0">
                <button
                  onClick={handleConfirmDataConsent}
                  disabled={isDataAuth}
                  className={cn(
                    "px-8 py-3 rounded-full font-medium transition-all",
                    isDataAuth
                      ? "bg-white/35 text-slate-500 border border-white/45"
                      : "bg-gradient-to-r from-purple-500 to-blue-600 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)]",
                  )}
                >
                  {isDataAuth ? "已同意" : "同意授权"}
                </button>
              </div>
            </div>

            <div className="bg-[linear-gradient(135deg,rgba(255,255,255,0.38),rgba(226,232,240,0.28))] border border-white/50 rounded-3xl p-6 relative overflow-hidden flex flex-col md:flex-row gap-6 text-slate-900 [backdrop-filter:blur(28px)_saturate(135%)]">
              <div className="text-4xl font-bold text-blue-400 opacity-60 absolute top-4 left-4">03</div>
              <div className="flex-1 pl-12">
                <div className="flex w-full justify-between items-center mb-1">
                  <h3 className="text-xl font-bold">问诊流程与医生选择</h3>
                  <StatusBadge isDone={isDoctorSelected} textDone="已选择" textPending="待选择" />
                </div>
                <p className="text-slate-700 text-sm mb-4">了解问诊流程，选择合适的询诊风格</p>

                <div className="flex items-center gap-2 mb-2 text-sm text-slate-800 flex-wrap">
                  <div className="bg-blue-500/20 px-3 py-1.5 rounded-lg flex flex-col min-w-[120px]">
                    <span className="text-blue-300 font-medium mb-1">❶ 基础问答</span>
                    <span className="text-xs text-slate-600">了解基本情况</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500/60" />
                  <div className="bg-blue-500/20 px-3 py-1.5 rounded-lg flex flex-col min-w-[120px]">
                    <span className="text-blue-300 font-medium mb-1">❷ 量表评估</span>
                    <span className="text-xs text-slate-600">
                      PHQ-9/SDQ/SAS
                      <br />
                      社会功能量表
                    </span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500/60" />
                  <div className="bg-blue-500/20 px-3 py-1.5 rounded-lg flex flex-col min-w-[120px]">
                    <span className="text-blue-300 font-medium mb-1">❸ 综合分析</span>
                    <span className="text-xs text-slate-600">
                      生成评估报告
                      <br />
                      与调节建议
                    </span>
                  </div>
                </div>
              </div>

              <div
                onClick={() => void handleSelectDoctorPersona()}
                className={cn(
                  "bg-white/28 border rounded-2xl p-4 flex gap-4 items-center shrink-0 w-full sm:w-auto mt-4 md:mt-0 transition-all cursor-pointer [backdrop-filter:blur(20px)_saturate(130%)]",
                  isDoctorSelected ? "border-blue-400 ring-2 ring-blue-500/50" : "border-white/10 hover:border-white/30",
                )}
              >
                <img
                  src="/home-digital-human.png"
                  alt="Doctor"
                  className="w-14 h-14 rounded-full object-cover border-2 border-blue-400/50"
                />
                <div className="flex flex-col">
                  <div className="font-bold text-lg">{displayedDoctorPersona?.display_name || "医生风格加载中"}</div>
                  <div className="text-slate-700 text-xs mb-1">
                    {selectedDoctorPersona
                      ? "已作为下次问诊默认数字医生"
                      : "点击选择并保存本次问诊风格"}
                  </div>
                  <div className="text-blue-400 text-xs text-left">
                    {doctorPersonas.length > 1 ? "点击切换风格 →" : "点击确认风格 →"}
                  </div>
                  {doctorSelectedAtText ? <div className="text-slate-500 text-[11px] mt-1">上次确认：{doctorSelectedAtText}</div> : null}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="w-full max-w-6xl mt-auto pt-6 pb-2 md:pb-4 flex flex-col sm:flex-row justify-center sm:justify-between items-center gap-6">
          <div className="bg-white/32 rounded-2xl p-4 border border-white/45 flex items-center gap-4 text-slate-800 [backdrop-filter:blur(22px)_saturate(130%)]">
            <div className="bg-blue-500/20 p-2 rounded-lg">
              <Check className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <div className="text-sm font-medium flex gap-2">
                准备状态 <span className="text-blue-400">{readyCount}/4</span>{" "}
                {readyCount === 4 ? <span className="text-green-400">已完成</span> : <span className="text-orange-400">进行中</span>}
              </div>
              <div className="w-48 h-1 bg-white/10 rounded-full mt-2 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-400 to-purple-500 transition-all duration-500" style={{ width: `${(readyCount / 4) * 100}%` }}></div>
              </div>
            </div>
            <p className="text-xs text-slate-600 ml-4 hidden md:block">完成全部准备后即可开始问诊</p>
          </div>

          <button
            onClick={handleStartConsultation}
            disabled={!isReady || state.loading}
            className={cn(
              "px-12 py-4 rounded-full font-bold text-xl flex items-center gap-2 transition-all duration-300",
              isReady && !state.loading
                ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 shadow-[0_0_30px_rgba(79,70,229,0.5)] hover:shadow-[0_0_40px_rgba(79,70,229,0.7)] hover:scale-105"
                : "bg-white/35 text-slate-500 border border-white/45 cursor-not-allowed",
            )}
          >
            {state.loading ? "处理中..." : "进入数字人问诊"} <ArrowRight className="w-6 h-6" />
          </button>

          <div className="bg-white/28 rounded-2xl p-4 border border-white/45 flex items-center gap-3 hidden lg:flex max-w-[280px] text-slate-800 [backdrop-filter:blur(22px)_saturate(130%)]">
            <ShieldAlert className="w-8 h-8 text-blue-300/60" />
            <p className="text-xs text-slate-600 leading-tight">问诊过程中可能暂时存储数据，我们将保护您的隐私安全。</p>
          </div>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col font-sans animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-6 pb-2 border-b border-slate-100">
              <div>
                <h2 className="text-2xl font-bold text-slate-800">信息录入</h2>
                <p className="text-sm text-slate-500">请补充或修改以下基础信息，用于本次问诊评估。</p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto max-h-[60vh] space-y-6">
              {formError ? (
                <div className="bg-red-50 border border-red-200 text-red-600 rounded-2xl px-4 py-3 text-sm">
                  {formError}
                </div>
              ) : null}

              <div>
                <h3 className="flex items-center gap-2 text-sm font-bold text-teal-600 px-3 py-1 bg-teal-50 w-fit rounded-full mb-4">
                  <div className="w-1.5 h-4 bg-teal-500 rounded-full"></div>
                  基础信息
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <InputField
                    label="1. 姓名"
                    value={formData.full_name}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, full_name: event.target.value })}
                    placeholder="张三"
                    icon={<User className="w-4 h-4" />}
                  />
                  <div className="flex flex-col gap-1.5">
                    <label className="text-sm font-medium text-slate-700 flex items-center gap-2">
                      <span className="text-teal-600">♂</span> 2. 性别
                    </label>
                    <select
                      value={formData.gender}
                      onChange={(event: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, gender: event.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all"
                    >
                      <option value="">请选择</option>
                      {GENDER_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                  <InputField
                    label="3. 年龄"
                    value={formData.age}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, age: event.target.value })}
                    placeholder="24"
                    type="number"
                    icon={<span className="text-slate-400 text-xs">📅</span>}
                  />
                  <InputField
                    label="4. 身高"
                    value={formData.height_cm}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, height_cm: event.target.value })}
                    placeholder="175"
                    append="cm"
                    icon={<Ruler className="w-4 h-4" />}
                  />
                  <InputField
                    label="5. 体重"
                    value={formData.weight_kg}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, weight_kg: event.target.value })}
                    placeholder="68"
                    append="kg"
                    icon={<Weight className="w-4 h-4" />}
                  />
                  <div className="flex flex-col gap-1.5">
                    <label className="text-sm font-medium text-slate-700 flex items-center gap-2">
                      <span className="text-teal-600">婚</span> 6. 婚姻状态
                    </label>
                    <select
                      value={formData.marital_status}
                      onChange={(event: React.ChangeEvent<HTMLSelectElement>) => setFormData({ ...formData, marital_status: event.target.value })}
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all"
                    >
                      <option value="">请选择</option>
                      {MARITAL_STATUS_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="flex items-center gap-2 text-sm font-bold text-teal-600 px-3 py-1 bg-teal-50 w-fit rounded-full mb-4">
                  <div className="w-1.5 h-4 bg-teal-500 rounded-full"></div>
                  家庭与就诊信息
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-sm font-medium text-slate-700 flex items-center gap-2">
                      <span className="text-teal-600">家</span> 7. 父母婚姻状态
                    </label>
                    <select
                      value={formData.parents_marital_status}
                      onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                        setFormData({ ...formData, parents_marital_status: event.target.value })
                      }
                      className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all"
                    >
                      <option value="">请选择</option>
                      {PARENTS_MARITAL_STATUS_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                  <InputField
                    label="8. 父母职业"
                    value={formData.parents_occupation}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                      setFormData({ ...formData, parents_occupation: event.target.value })
                    }
                    placeholder="如：教师、务工、个体经营"
                    icon={<span className="text-slate-400 text-xs">业</span>}
                  />
                  <div className="flex flex-col gap-2 sm:col-span-2">
                    <label className="text-sm font-medium text-slate-700 flex items-center gap-2">
                      <span className="text-teal-600">♡</span> 9. 是否曾因心理/精神问题就诊
                    </label>
                    <div className="flex bg-slate-100 rounded-xl p-1 gap-1">
                      {PRIOR_PSYCHIATRIC_VISIT_OPTIONS.map((option) => (
                        <button
                          key={option}
                          type="button"
                          onClick={() => setFormData({ ...formData, prior_psychiatric_visit: option })}
                          className={cn(
                            "flex-1 py-2 text-sm font-medium rounded-lg transition-colors",
                            formData.prior_psychiatric_visit === option
                              ? "bg-white text-teal-600 shadow-sm"
                              : "text-slate-500 hover:text-slate-700",
                          )}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-slate-100 flex gap-4 justify-center sm:justify-end bg-slate-50/50">
              <button
                onClick={() => setIsModalOpen(false)}
                className="px-8 py-3 rounded-full font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 transition-colors hidden sm:block"
              >
                取消
              </button>
              <button
                onClick={handleSaveProfile}
                disabled={state.loading}
                className={cn(
                  "w-full sm:w-auto px-10 py-3 rounded-full font-medium text-white transition-all",
                  state.loading
                    ? "bg-slate-300 cursor-not-allowed"
                    : "bg-gradient-to-r from-blue-600 to-purple-600 hover:shadow-lg",
                )}
              >
                {state.loading ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConsultationLayout>
  );
}

function StatusBadge({ isDone, textDone, textPending }: { isDone: boolean; textDone: string; textPending: string }) {
  if (isDone) {
    return (
      <span className="bg-green-500/20 text-green-400 px-3 py-1 text-xs rounded-full border border-green-500/30 flex items-center gap-1">
        <Check className="w-3 h-3" /> {textDone}
      </span>
    );
  }
  return (
    <span className="bg-orange-500/20 text-orange-400 px-3 py-1 text-xs rounded-full border border-orange-500/30 flex items-center gap-1">
      <AlertCircle className="w-3 h-3" /> {textPending}
    </span>
  );
}

function DeviceIcon({
  icon,
  label,
  statusText,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  statusText: string;
  tone: DeviceIndicatorTone;
}) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className={cn(
          "p-2 rounded-lg",
          tone === "ready" && "text-green-300 bg-green-400/10",
          tone === "pending" && "text-blue-200 bg-blue-400/10",
          tone === "warning" && "text-orange-300 bg-orange-400/10",
          tone === "error" && "text-red-300 bg-red-400/10",
        )}
      >
        {icon}
      </div>
      <span className="text-xs text-slate-700">{label}</span>
      <span
        className={cn(
          "text-[11px]",
          tone === "ready" && "text-green-300",
          tone === "pending" && "text-blue-200",
          tone === "warning" && "text-orange-300",
          tone === "error" && "text-red-300",
        )}
      >
        {statusText}
      </span>
    </div>
  );
}

function InfoCard({ icon, label, value, className }: { icon: React.ReactNode; label: string; value: string; className?: string }) {
  return (
    <div className={cn("bg-white/24 border border-white/35 rounded-xl p-3 flex items-center gap-3 [backdrop-filter:blur(16px)_saturate(125%)]", className)}>
      <div className="bg-blue-500/20 p-2 rounded-lg text-white">{icon}</div>
      <div className="flex flex-col">
        <span className="text-xs text-slate-600">{label}</span>
        <span className="text-sm font-medium text-slate-900 truncate">{value}</span>
      </div>
    </div>
  );
}

function InputField({
  label,
  value,
  onChange,
  placeholder,
  append,
  type = "text",
  icon,
}: {
  label: string;
  value: string;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder: string;
  append?: string;
  type?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-slate-700 flex items-center gap-2">
        {icon && <span className="text-slate-400">{icon}</span>}
        {label}
      </label>
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all placeholder:text-slate-300"
        />
        {append && <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm">{append}</span>}
      </div>
    </div>
  );
}
