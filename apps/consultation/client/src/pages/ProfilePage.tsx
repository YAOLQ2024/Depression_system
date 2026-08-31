import { motion } from "motion/react";
import {
  AlertCircle,
  ArrowRight,
  Camera,
  CheckCircle2,
  ClipboardList,
  Clock3,
  Mic,
  Monitor,
  ShieldCheck,
  Stethoscope,
  User,
  Volume2,
} from "lucide-react";
import { useMemo, type ElementType, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { Header } from "../components/Header";
import { getProfileStatusLabel, getRoleLabel, getUserDisplayName, getUserInitial } from "../lib/account";
import { getPermissionStatusLabel, type PreparationPermissionState } from "../lib/preparationDeviceAccess";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";

type StoredMediaChannel = {
  permission?: PreparationPermissionState;
  available?: boolean | null;
  detectedCount?: number;
  ready?: boolean;
};

type StoredSpeakerState = {
  available?: boolean | null;
  detectedCount?: number;
  supported?: boolean;
};

type StoredDeviceStatus = {
  status?: string;
  checked_at?: string;
  browser_ready?: boolean;
  secure_context?: boolean;
  media_devices_supported?: boolean;
  camera?: StoredMediaChannel;
  microphone?: StoredMediaChannel;
  speaker?: StoredSpeakerState;
};

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function getDisplayValue(value: string | number | null | undefined) {
  if (value === null || value === undefined) {
    return "未填写";
  }

  const normalized = String(value).trim();
  return normalized || "未填写";
}

function getChannelStatusText(channel?: StoredMediaChannel | null) {
  if (!channel) {
    return "待检测";
  }

  if (channel.ready) {
    return "已授权";
  }

  if (channel.available === false) {
    return "未检测到设备";
  }

  if (channel.permission) {
    return getPermissionStatusLabel(channel.permission);
  }

  return "待检测";
}

function getSpeakerStatusText(speaker?: StoredSpeakerState | null) {
  if (!speaker) {
    return "待检测";
  }

  return speaker.available ? "已检测" : "未检测到设备";
}

function getBrowserStatusText(deviceStatus?: StoredDeviceStatus | null) {
  if (!deviceStatus) {
    return "待检测";
  }

  if (deviceStatus.browser_ready) {
    return "已就绪";
  }

  if (deviceStatus.secure_context === false) {
    return "需安全上下文";
  }

  if (deviceStatus.media_devices_supported === false) {
    return "浏览器不支持";
  }

  return "待检查";
}

function getConsultationStatusLabel(status?: string | null) {
  switch (status) {
    case "handoff_ready":
      return "问诊完成，待进入量表";
    case "in_progress":
      return "问诊进行中";
    case "paused":
      return "问诊已暂停";
    case "completed":
      return "问诊已完成";
    default:
      return status ? status : "未开始";
  }
}

function getAssessmentStatusLabel(status?: string | null) {
  switch (status) {
    case "completed":
      return "量表已完成";
    case "in_progress":
      return "量表进行中";
    case "draft":
      return "量表待开始";
    default:
      return status ? status : "未开始";
  }
}

function getLatestTimestamp(values: Array<string | null | undefined>) {
  return values
    .filter((value): value is string => Boolean(value))
    .map((value) => ({ raw: value, time: new Date(value).getTime() }))
    .filter((item) => !Number.isNaN(item.time))
    .sort((a, b) => b.time - a.time)[0]?.raw;
}

function BackgroundDecor() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-[400px] bg-gradient-to-b from-violet-100/60 via-blue-50/40 to-transparent" />
      <div className="absolute -left-32 top-[120px] h-[500px] w-[500px] rounded-full bg-violet-200/30 blur-[100px]" />
      <div className="absolute -right-32 top-[60px] h-[420px] w-[420px] rounded-full bg-blue-200/25 blur-[100px]" />
      <div className="absolute left-1/2 top-[320px] h-[300px] w-[620px] -translate-x-1/2 rounded-full bg-indigo-100/20 blur-[80px]" />
      <svg className="absolute inset-0 h-full w-full opacity-30" xmlns="http://www.w3.org/2000/svg">
        <circle cx="11%" cy="23%" r="3" fill="#8b5cf6" opacity="0.38" />
        <circle cx="86%" cy="16%" r="4" fill="#6366f1" opacity="0.28" />
        <circle cx="74%" cy="54%" r="2.5" fill="#3b82f6" opacity="0.32" />
        <circle cx="18%" cy="70%" r="3.5" fill="#8b5cf6" opacity="0.22" />
      </svg>
    </div>
  );
}

function LightCard({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("rounded-2xl bg-white/82 shadow-sm ring-1 ring-black/[0.04] backdrop-blur-sm", className)}>{children}</div>;
}

function Section({
  icon: Icon,
  title,
  subtitle,
  children,
  delay = 0,
  action,
  className,
  cardClassName,
  contentClassName,
}: {
  icon: ElementType;
  title: string;
  subtitle?: string;
  children: ReactNode;
  delay?: number;
  action?: ReactNode;
  className?: string;
  cardClassName?: string;
  contentClassName?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
    >
      <LightCard className={cn("p-5 md:p-6", cardClassName)}>
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-100 text-violet-500">
              <Icon className="h-4.5 w-4.5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-slate-900">{title}</h2>
              {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
            </div>
          </div>
          {action}
        </div>
        <div className={contentClassName}>{children}</div>
      </LightCard>
    </motion.div>
  );
}

function FieldCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50/85 p-4 ring-1 ring-black/[0.03]">
      <div className="text-xs font-medium text-slate-400">{label}</div>
      <div className="mt-2 text-sm font-medium text-slate-700">{value}</div>
    </div>
  );
}

function StatusRow({
  label,
  value,
  done,
}: {
  label: string;
  value: string;
  done?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl bg-slate-50/85 px-4 py-3 ring-1 ring-black/[0.03]">
      <div className="flex min-w-0 items-start gap-2.5">
        <div className={cn("mt-0.5 shrink-0", done ? "text-emerald-500" : "text-amber-500")}>
          {done ? <CheckCircle2 className="h-4.5 w-4.5" /> : <AlertCircle className="h-4.5 w-4.5" />}
        </div>
        <span className="text-sm text-slate-600">{label}</span>
      </div>
      <span className={cn("shrink-0 text-sm font-medium", done ? "text-emerald-600" : "text-slate-500")}>{value}</span>
    </div>
  );
}

function QuickActionButton({
  title,
  description,
  onClick,
}: {
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3.5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-violet-200 hover:bg-violet-50/70"
    >
      <div className="min-w-0">
        <div className="text-sm font-semibold text-slate-800">{title}</div>
        <div className="mt-1 text-xs text-slate-500">{description}</div>
      </div>
      <ArrowRight className="h-4.5 w-4.5 shrink-0 text-violet-500" />
    </button>
  );
}

export default function ProfilePage() {
  const { state } = useConsultationAppContext();
  const navigate = useNavigate();

  const user = state.user;
  const profile = user?.profile || null;
  const preparationState = user?.preparation_state || null;
  const deviceStatus = (preparationState?.device_status as StoredDeviceStatus | undefined) || null;
  const doctorPersonas = state.bootstrap?.doctor_personas || [];
  const selectedDoctorId = preparationState?.assigned_doctor_persona || null;
  const selectedDoctor =
    doctorPersonas.find((persona) => persona.persona_id === selectedDoctorId)?.display_name || selectedDoctorId || "未选择";

  const profileReady = user?.profile_status === "completed";
  const deviceReady = deviceStatus?.status === "authorized";
  const consentReady = Boolean(preparationState?.consent_confirmed);
  const doctorReady = Boolean(selectedDoctorId);
  const readyCount = [profileReady, deviceReady, consentReady, doctorReady].filter(Boolean).length;
  const readyPercent = Math.round((readyCount / 4) * 100);

  const userDisplayName = getUserDisplayName(user);
  const userInitial = getUserInitial(user);
  const profileStatusLabel = getProfileStatusLabel(user?.profile_status);
  const roleLabel = getRoleLabel(user?.role);
  const sessionModeLabel = state.keepLoggedIn ? "长期登录" : "仅当前浏览器会话";
  const consultationStatusLabel = getConsultationStatusLabel(state.consultation?.status);
  const assessmentStatusLabel = getAssessmentStatusLabel(state.assessment?.status);
  const latestSyncAt = useMemo(
    () =>
      getLatestTimestamp([
        preparationState?.updated_at,
        preparationState?.doctor_selected_at,
        preparationState?.consent_confirmed_at,
        deviceStatus?.checked_at,
        state.consultation?.updated_at,
        state.assessment?.updated_at,
      ]),
    [
      deviceStatus?.checked_at,
      preparationState?.consent_confirmed_at,
      preparationState?.doctor_selected_at,
      preparationState?.updated_at,
      state.assessment?.updated_at,
      state.consultation?.updated_at,
    ],
  );

  const overviewItems = [
    { label: "账号角色", value: roleLabel },
    { label: "档案状态", value: profileStatusLabel },
    { label: "当前入口", value: state.homeEntryLabel },
    { label: "最近同步", value: formatDateTime(latestSyncAt) },
  ];

  const preparationFieldItems = [
    { label: "账号名", value: getDisplayValue(user?.full_name) },
    { label: "性别", value: getDisplayValue(profile?.gender) },
    { label: "年龄", value: profile?.age ? `${profile.age} 岁` : "未填写" },
    { label: "身高", value: profile?.height_cm ? `${profile.height_cm} cm` : "未填写" },
    { label: "体重", value: profile?.weight_kg ? `${profile.weight_kg} kg` : "未填写" },
    { label: "婚姻状态", value: getDisplayValue(profile?.marital_status) },
    { label: "父母婚姻状态", value: getDisplayValue(profile?.parents_marital_status) },
    { label: "父母职业", value: getDisplayValue(profile?.parents_occupation) },
    { label: "既往心理/精神就诊", value: getDisplayValue(profile?.prior_psychiatric_visit) },
  ];

  const deviceItems = [
    { label: "浏览器环境", value: getBrowserStatusText(deviceStatus), icon: <Monitor className="h-4 w-4" /> },
    { label: "摄像头", value: getChannelStatusText(deviceStatus?.camera), icon: <Camera className="h-4 w-4" /> },
    { label: "麦克风", value: getChannelStatusText(deviceStatus?.microphone), icon: <Mic className="h-4 w-4" /> },
    { label: "扬声器", value: getSpeakerStatusText(deviceStatus?.speaker), icon: <Volume2 className="h-4 w-4" /> },
  ];

  const accountItems = [
    { label: "登录邮箱", value: getDisplayValue(user?.email) },
    { label: "登录方式", value: sessionModeLabel },
    { label: "用户编号", value: getDisplayValue(user?.id) },
    { label: "问诊状态", value: consultationStatusLabel },
    { label: "量表状态", value: assessmentStatusLabel },
    { label: "数字医生风格", value: selectedDoctor },
  ];

  return (
    <div className="min-h-screen bg-[#f8f7ff]">
      <BackgroundDecor />

      <div className="relative z-20">
        <Header title="个人档案" />
      </div>

      <div className="relative z-10 w-full px-6 pt-6 pb-10 md:px-10 lg:px-14">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <LightCard className="overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-violet-400 via-blue-400 to-violet-400" />
            <div className="p-6 md:p-7">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex min-w-0 flex-col gap-5 md:flex-row md:items-start">
                  <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-[28px] bg-gradient-to-br from-violet-500 to-blue-500 text-3xl font-semibold text-white shadow-lg shadow-violet-500/20">
                    {userInitial}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h1 className="text-2xl font-semibold tracking-tight text-slate-900 md:text-3xl">{userDisplayName}</h1>
                      <span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-medium text-violet-600 ring-1 ring-violet-200">
                        {profileStatusLabel}
                      </span>
                      <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-600 ring-1 ring-blue-200">
                        {roleLabel}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-7 text-slate-500">
                      这里集中展示账号信息、问诊准备页已保存内容、设备授权状态以及当前流程入口，便于在开始或继续评估前快速确认。
                    </p>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                      {overviewItems.map((item) => (
                        <FieldCard key={item.label} label={item.label} value={item.value} />
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:w-[360px]">
                  <QuickActionButton
                    title={state.homeEntryLabel}
                    description="继续当前流程"
                    onClick={() => navigate(state.homeEntryPath)}
                  />
                  <QuickActionButton
                    title="编辑问诊准备"
                    description="回到准备页补充或修改信息"
                    onClick={() => navigate(APP_PATHS.preparation)}
                  />
                  <QuickActionButton
                    title="查看历史记录"
                    description="回看既往问诊与评估结果"
                    onClick={() => navigate(APP_PATHS.history)}
                  />
                  <QuickActionButton
                    title="进入调节干预"
                    description="查看干预入口与后续调节内容"
                    onClick={() => navigate(APP_PATHS.intervention)}
                  />
                </div>
              </div>
            </div>
          </LightCard>
        </motion.div>

        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_360px] xl:items-stretch">
          <div className="space-y-4">
            <Section
              icon={ClipboardList}
              title="问诊准备信息"
              subtitle="以下内容来自问诊准备页，后续如需修改可直接返回准备页编辑。"
              delay={0.1}
              action={
                <button
                  type="button"
                  onClick={() => navigate(APP_PATHS.preparation)}
                  className="rounded-lg bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-600 ring-1 ring-violet-200 transition-all hover:bg-violet-100"
                >
                  去修改
                </button>
              }
            >
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {preparationFieldItems.map((item) => (
                  <FieldCard key={item.label} label={item.label} value={item.value} />
                ))}
              </div>
            </Section>

            <Section
              icon={ShieldCheck}
              title="准备状态与授权"
              subtitle="量表和数字人问诊都会依赖这里的设备检查、知情同意与医生风格配置。"
              delay={0.16}
            >
              <div className="grid gap-3 md:grid-cols-2">
                <StatusRow label="数据采集同意" value={consentReady ? "已同意" : "待确认"} done={consentReady} />
                <StatusRow label="数字医生风格" value={doctorReady ? selectedDoctor : "待选择"} done={doctorReady} />
                <StatusRow
                  label="设备授权时间"
                  value={formatDateTime(deviceStatus?.checked_at)}
                  done={Boolean(deviceStatus?.checked_at)}
                />
                <StatusRow
                  label="同意确认时间"
                  value={formatDateTime(preparationState?.consent_confirmed_at)}
                  done={Boolean(preparationState?.consent_confirmed_at)}
                />
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {deviceItems.map((item) => (
                  <div key={item.label} className="rounded-xl bg-slate-50/85 p-4 ring-1 ring-black/[0.03]">
                    <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                      <span className="text-violet-500">{item.icon}</span>
                      {item.label}
                    </div>
                    <div className="mt-2 text-sm font-medium text-slate-700">{item.value}</div>
                  </div>
                ))}
              </div>
            </Section>

            <Section
              icon={User}
              title="账号与系统信息"
              subtitle="补充展示常见个人中心会关心的账号标识、登录偏好与当前系统状态。"
              delay={0.22}
            >
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {accountItems.map((item) => (
                  <FieldCard key={item.label} label={item.label} value={item.value} />
                ))}
              </div>
            </Section>
          </div>

          <div className="space-y-4 xl:flex xl:h-full xl:flex-col">
            <Section
              icon={ShieldCheck}
              title="准备完成度"
              subtitle="当前按 4 个准备项计算，后续如果有必做项要求也可以在这里继续扩展。"
              delay={0.12}
            >
              <div className="rounded-2xl bg-gradient-to-br from-violet-50 via-white to-blue-50 p-5 ring-1 ring-violet-100">
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <div className="text-sm font-medium text-slate-500">已完成</div>
                    <div className="mt-1 text-3xl font-semibold text-slate-900">
                      {readyCount}
                      <span className="ml-1 text-lg font-medium text-slate-400">/ 4</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-medium text-slate-400">完成率</div>
                    <div className="mt-1 text-2xl font-semibold text-violet-600">{readyPercent}%</div>
                  </div>
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/90 ring-1 ring-black/[0.04]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-500 to-blue-500 transition-all duration-500"
                    style={{ width: `${readyPercent}%` }}
                  />
                </div>
                <div className="mt-4 space-y-2">
                  <StatusRow label="基础档案" value={profileReady ? "已完成" : "待完善"} done={profileReady} />
                  <StatusRow label="设备授权" value={deviceReady ? "已就绪" : "待检查"} done={deviceReady} />
                  <StatusRow label="数据授权" value={consentReady ? "已确认" : "待确认"} done={consentReady} />
                  <StatusRow label="医生风格" value={doctorReady ? "已选择" : "待选择"} done={doctorReady} />
                </div>
              </div>
            </Section>

            <Section
              icon={Stethoscope}
              title="当前流程"
              subtitle="这里用来解释系统下一步会把您带到哪里。"
              delay={0.18}
              className="xl:flex-1"
              cardClassName="xl:flex xl:h-full xl:flex-col"
              contentClassName="xl:flex-1"
            >
              <div className="flex h-full flex-col gap-3 xl:justify-between">
                <div className="rounded-xl bg-slate-50/85 p-4 ring-1 ring-black/[0.03]">
                  <div className="text-xs font-medium text-slate-400">下一步入口</div>
                  <div className="mt-2 text-sm font-semibold text-slate-800">{state.homeEntryLabel}</div>
                  <p className="mt-1 text-xs leading-6 text-slate-500">
                    系统会根据当前会话状态自动续接；如果需要重新开始，也可以回到首页直接新建会话。
                  </p>
                </div>
                <div className="rounded-xl bg-slate-50/85 p-4 ring-1 ring-black/[0.03]">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                    <Clock3 className="h-4 w-4 text-violet-500" />
                    问诊阶段
                  </div>
                  <div className="mt-2 text-sm text-slate-600">{consultationStatusLabel}</div>
                </div>
                <div className="rounded-xl bg-slate-50/85 p-4 ring-1 ring-black/[0.03]">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                    <ClipboardList className="h-4 w-4 text-violet-500" />
                    量表阶段
                  </div>
                  <div className="mt-2 text-sm text-slate-600">{assessmentStatusLabel}</div>
                </div>
              </div>
            </Section>
          </div>
        </div>
      </div>
    </div>
  );
}
