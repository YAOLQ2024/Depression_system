import { useState } from "react";
import { ClipboardList, MessageSquareHeart, PlusCircle, Sparkles, UserCheck } from "lucide-react";
import { motion } from "motion/react";
import { useNavigate } from "react-router-dom";

import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { Header } from "../components/Header";
import { HomeOrbitalMenu, type HomeOrbitalMenuItem } from "../components/home/HomeOrbitalMenu";
import { HomePortal } from "../components/home/HomePortal";
import { getUserDisplayName } from "../lib/account";
import { APP_PATHS } from "../routes";
import type { CreateConsultationSessionPayload } from "../services/api/contracts";

type StoredMediaChannel = { ready?: boolean };
type StoredSpeakerState = { available?: boolean | null };
type StoredDeviceStatus = {
  status?: string;
  browser_ready?: boolean;
  microphone?: StoredMediaChannel;
  speaker?: StoredSpeakerState;
};

function getHomeSubtitle({
  profileStatus,
  consultationStatus,
  assessmentStatus,
}: {
  profileStatus?: string;
  consultationStatus?: string | null;
  assessmentStatus?: string | null;
}) {
  if (assessmentStatus === "completed") return "本轮评估已完成，可查看最新结果与建议。";
  if (assessmentStatus) return "量表问诊进行中，可继续完成剩余题目。";
  if (consultationStatus === "handoff_ready") return "规则问诊已完成，可继续进入量表评估。";
  if (consultationStatus) return "数字人问诊正在进行，随时可以继续当前会话。";
  if (profileStatus !== "completed") return "完成准备信息后，即可开始正式评估。";
  return "设备与档案已准备就绪，可以开始本次心理评估。";
}

function buildNewConsultationPayload(
  profileStatus?: string,
  preparationState?: {
    device_status?: Record<string, unknown>;
    consent_confirmed?: boolean;
    assigned_doctor_persona?: string | null;
  } | null,
): CreateConsultationSessionPayload | null {
  const deviceStatus = (preparationState?.device_status as StoredDeviceStatus | undefined) || null;
  const ready = Boolean(
    profileStatus === "completed" &&
      preparationState?.consent_confirmed &&
      preparationState?.assigned_doctor_persona &&
      deviceStatus?.status === "authorized",
  );
  if (!ready || !deviceStatus) return null;

  return {
    device_status: preparationState?.device_status,
    audio_channel_ready: Boolean(
      deviceStatus.browser_ready && deviceStatus.microphone?.ready && (deviceStatus.speaker?.available ?? true),
    ),
    consent_confirmed: Boolean(preparationState?.consent_confirmed),
    consultation_ready_state: "ready",
    assigned_doctor_persona: preparationState?.assigned_doctor_persona || null,
  };
}

export default function HomePage() {
  const { state, actions } = useConsultationAppContext();
  const navigate = useNavigate();
  const [selectedIndex, setSelectedIndex] = useState(2);
  const userDisplayName = getUserDisplayName(state.user);
  const heroSubtitle = getHomeSubtitle({
    profileStatus: state.user?.profile_status,
    consultationStatus: state.consultation?.status,
    assessmentStatus: state.assessment?.status,
  });
  const hasActiveSession = Boolean(state.consultation?.status || state.assessment?.status);

  const handleStartConsultation = () => navigate(state.homeEntryPath);
  const handleOpenHistory = () => navigate(APP_PATHS.history);
  const handleOpenIntervention = () =>
    navigate(APP_PATHS.intervention, { state: { source: "home_direct", bindConsultation: false } });
  const handleOpenProfile = () => navigate(APP_PATHS.profile);
  const handleCreateNewConsultation = async () => {
    if (state.loading) return;
    const payload = buildNewConsultationPayload(state.user?.profile_status, state.user?.preparation_state);
    if (!payload) {
      navigate(APP_PATHS.preparation);
      return;
    }
    const started = await actions.handleStartConsultation(payload);
    if (started) navigate(APP_PATHS.consultation, { state: { sessionId: started.session_id } });
  };

  // Order and all orbital positions deliberately mirror the packaged reference homepage.
  const menuItems: HomeOrbitalMenuItem[] = [
    { id: "history", title: "历史记录", subtitle: "查看过往评估记录与健康档案", badge: "已归档", estimatedTime: "数据完整", iconTone: "from-blue-500 to-cyan-400", icon: <ClipboardList className="h-5 w-5" />, onAction: handleOpenHistory },
    { id: "new", title: "新建会话", subtitle: "开启全新多模态辅助评估", badge: "标准量表", estimatedTime: "约需 10 分钟", iconTone: "from-violet-500 to-fuchsia-500", icon: <PlusCircle className="h-5 w-5" />, onAction: () => void handleCreateNewConsultation() },
    { id: "continue", title: state.homeEntryLabel, subtitle: hasActiveSession ? "接续当前数字人陪伴式评估" : "开始数字人陪伴式评估", badge: hasActiveSession ? "进行中" : "准备就绪", estimatedTime: hasActiveSession ? "约需 8–10 分钟" : "准备完成后开始", iconTone: "from-sky-500 to-indigo-600", icon: <MessageSquareHeart className="h-5 w-5" />, onAction: handleStartConsultation },
    { id: "intervention", title: "调节干预", subtitle: "进入情绪调节与正念体验", badge: "4 项定制训练", estimatedTime: "随时开始", iconTone: "from-emerald-500 to-teal-400", icon: <Sparkles className="h-5 w-5" />, onAction: handleOpenIntervention },
    { id: "profile", title: "个人档案", subtitle: "查看个人资料与隐私设置", badge: "隐私保护开启", estimatedTime: "资料已加密", iconTone: "from-rose-500 to-pink-500", icon: <UserCheck className="h-5 w-5" />, onAction: handleOpenProfile },
  ];
  const selectedItem = menuItems[selectedIndex] || menuItems[2];

  return (
    <div className="relative z-0 flex h-screen w-full select-none flex-col overflow-hidden bg-[#4c3a30] font-sans text-slate-800">
      <img src="/4K.png" alt="" aria-hidden="true" fetchPriority="high" className="absolute inset-0 z-0 h-full w-full object-cover object-center" />
      <div className="pointer-events-none absolute inset-0 z-[1] bg-[linear-gradient(90deg,rgba(8,26,51,0.14),transparent_47%,rgba(8,26,51,0.12))]" />
      <div className="relative z-20 w-full"><Header theme="dark" title="首页" /></div>

      <main className="relative z-10 mx-auto grid min-h-0 w-full max-w-[1920px] flex-1 grid-cols-12 items-center overflow-hidden px-4 sm:px-8">
        <section className="relative col-span-12 flex h-full items-center justify-start lg:col-span-7" aria-label="数字人助手">
          <HomePortal activeMenuTitle={selectedItem.title} onAvatarClick={selectedItem.onAction} />
        </section>

        <section className="relative z-20 col-span-12 flex h-full items-center justify-start lg:col-span-5" aria-label="首页功能入口">
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }} className="pointer-events-auto absolute right-2 top-3 z-30 text-right sm:right-8 sm:top-5">
            <div className="flex flex-col items-end">
              <div className="mb-1.5 inline-flex items-center gap-2 text-xs font-medium text-sky-100 drop-shadow-[0_2px_5px_rgba(15,23,42,0.65)]">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-300 shadow-[0_0_8px_#67e8f9]" />
                <span className="tracking-wide">数字健康随访通道</span><span className="text-white/70">/</span><span className="font-mono text-[11px] text-white/90">当前会话已保留</span>
              </div>
              <h1 className="flex items-center gap-2.5 text-xl font-bold tracking-tight text-white drop-shadow-[0_2px_7px_rgba(15,23,42,0.82)] sm:text-2xl"><span>你好，{userDisplayName}</span><span className="rounded-md border border-white/45 bg-gradient-to-r from-sky-500/90 to-indigo-500/90 px-2 py-0.5 text-sm font-medium text-white shadow-[0_3px_10px_rgba(37,99,235,0.35)]">阶段二</span></h1>
              <p className="mt-1 max-w-[360px] text-xs font-normal tracking-wide text-white/95 drop-shadow-[0_2px_5px_rgba(15,23,42,0.75)] sm:text-sm">{heroSubtitle}</p>
            </div>
          </motion.div>
          <div className="flex h-full w-full -translate-y-10 items-center justify-start sm:-translate-y-14 lg:-translate-y-16">
            <HomeOrbitalMenu items={menuItems} selectedIndex={selectedIndex} onSelectIndex={setSelectedIndex} />
          </div>
        </section>
      </main>
    </div>
  );
}
