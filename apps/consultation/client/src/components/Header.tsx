import { Bell, ChevronDown } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { showProfileModal } from "./ProfileModal";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { getProfileStatusLabel, getUserDisplayName, getUserInitial } from "../lib/account";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";

interface HeaderProps {
  theme?: 'light' | 'dark';
  title?: string | null | false;
}

export function Header({ theme = 'light', title }: HeaderProps) {
  const { state } = useConsultationAppContext();
  const navigate = useNavigate();
  const location = useLocation();
  const isDark = theme === 'dark';
  const userDisplayName = getUserDisplayName(state.user);
  const profileStatusLabel = getProfileStatusLabel(state.user?.profile_status);
  const userInitial = getUserInitial(state.user);

  const handleLogoClick = () => {
    if (location.pathname !== APP_PATHS.home) {
      navigate(APP_PATHS.home);
    }
  };

  return (
    <header className="relative z-10 flex h-[clamp(56px,4.2vw,88px)] w-full items-center justify-between px-[clamp(12px,1.25vw,30px)]">
      <div className="flex min-w-0 -translate-y-[clamp(6px,0.55vw,12px)] cursor-pointer items-center gap-[clamp(8px,0.7vw,16px)]" onClick={handleLogoClick}>
        <div className="h-[clamp(28px,2.2vw,48px)] w-[clamp(58px,4vw,84px)] shrink-0 overflow-hidden">
          <img
            src="/aim-brand-lockup-transparent-clean.png"
            alt="AIM"
            className="h-full w-auto max-w-none object-contain object-left drop-shadow-[0_1px_4px_rgba(255,255,255,0.16)]"
          />
        </div>
        <div className="flex min-w-0 items-center gap-[clamp(8px,0.7vw,16px)]">
          <h1 className={cn("shrink-0 text-[clamp(14px,1.05vw,24px)] font-semibold leading-tight", isDark ? "text-white" : "text-slate-800")}>
            抑郁症数字人辅助评估系统
          </h1>
          {title !== false ? (
            <div className="flex min-w-0 items-center gap-[clamp(8px,0.7vw,16px)]">
              <span className={cn("h-[clamp(16px,1.25vw,28px)] w-px rounded-full", isDark ? "bg-white/20" : "bg-slate-300")} />
              <span className={cn("truncate text-[clamp(12px,0.85vw,19px)] font-normal", isDark ? "text-white/70" : "text-slate-500")}>
                {title || "量表问诊"}
              </span>
            </div>
          ) : null}
        </div>
      </div>
      
      <div className="flex -translate-y-[clamp(6px,0.55vw,12px)] items-center gap-[clamp(10px,1vw,24px)]">
        <button className={cn("relative p-[clamp(5px,0.4vw,10px)] transition-colors", isDark ? "text-white/70 hover:text-white" : "text-slate-500 hover:text-primary-600")}>
          <Bell className="h-[clamp(18px,1.35vw,30px)] w-[clamp(18px,1.35vw,30px)]" />
          <span className="sr-only">消息</span>
        </button>
        
        <button
          type="button"
          onClick={(event) => showProfileModal(event.currentTarget)}
          className="group flex cursor-pointer items-center gap-[clamp(7px,0.6vw,14px)] rounded-full p-[clamp(4px,0.35vw,8px)] transition-colors hover:bg-white/10 md:pr-[clamp(10px,0.9vw,20px)]"
        >
          <div
            className={cn(
              "flex h-[clamp(30px,2.25vw,50px)] w-[clamp(30px,2.25vw,50px)] items-center justify-center rounded-full border text-[clamp(13px,0.95vw,21px)] font-semibold shadow-sm",
              isDark ? "border-white/20 bg-white/10 text-white" : "border-slate-200 bg-primary-50 text-primary-700",
            )}
          >
            {userInitial}
          </div>
          <div className="hidden md:flex flex-col items-start leading-tight">
            <span className={cn("text-[clamp(13px,0.95vw,21px)] font-medium transition-colors", isDark ? "text-white/90 group-hover:text-white" : "text-slate-700 group-hover:text-primary-600")}>
              {userDisplayName}
            </span>
            <span className={cn("text-[clamp(10px,0.7vw,15px)]", isDark ? "text-white/60 group-hover:text-white/80" : "text-slate-400 group-hover:text-slate-500")}>
              {profileStatusLabel}
            </span>
          </div>
          <ChevronDown className={cn("h-[clamp(15px,1.1vw,24px)] w-[clamp(15px,1.1vw,24px)] transition-colors", isDark ? "text-white/60 group-hover:text-white" : "text-slate-400 group-hover:text-primary-600")} />
        </button>
      </div>
    </header>
  );
}
