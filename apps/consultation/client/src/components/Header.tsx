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
    <header className="relative z-10 flex h-[60px] w-full items-center justify-between px-4 md:px-5">
      <div className="flex min-w-0 items-center gap-2.5 cursor-pointer" onClick={handleLogoClick}>
        <img
          src="/aim-brand-lockup.svg"
          alt="医学人工智能实验室"
          className="h-[34px] w-auto shrink-0 object-contain drop-shadow-[0_1px_4px_rgba(255,255,255,0.2)] md:h-[38px]"
        />
        <div className="flex min-w-0 items-center gap-2.5">
          <h1 className={cn("shrink-0 text-base font-semibold leading-tight", isDark ? "text-white" : "text-slate-800")}>
            抑郁症数字人辅助评估系统
          </h1>
          {title !== false ? (
            <div className="flex min-w-0 items-center gap-2.5">
              <span className={cn("h-4 w-px rounded-full", isDark ? "bg-white/20" : "bg-slate-300")} />
              <span className={cn("truncate text-[13px] font-normal", isDark ? "text-white/70" : "text-slate-500")}>
                {title || "量表问诊"}
              </span>
            </div>
          ) : null}
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <button className={cn("relative p-1.5 transition-colors", isDark ? "text-white/70 hover:text-white" : "text-slate-500 hover:text-primary-600")}>
          <Bell className="w-5 h-5" />
          <span className="sr-only">消息</span>
        </button>
        
        <button
          type="button"
          onClick={(event) => showProfileModal(event.currentTarget)}
          className="flex items-center gap-2 cursor-pointer group hover:bg-white/10 p-1 md:pr-3 rounded-full transition-colors"
        >
          <div
            className={cn(
              "w-8 h-8 rounded-full border flex items-center justify-center text-sm font-semibold shadow-sm",
              isDark ? "border-white/20 bg-white/10 text-white" : "border-slate-200 bg-primary-50 text-primary-700",
            )}
          >
            {userInitial}
          </div>
          <div className="hidden md:flex flex-col items-start leading-tight">
            <span className={cn("text-sm font-medium transition-colors", isDark ? "text-white/90 group-hover:text-white" : "text-slate-700 group-hover:text-primary-600")}>
              {userDisplayName}
            </span>
            <span className={cn("text-[11px]", isDark ? "text-white/60 group-hover:text-white/80" : "text-slate-400 group-hover:text-slate-500")}>
              {profileStatusLabel}
            </span>
          </div>
          <ChevronDown className={cn("w-4 h-4 transition-colors", isDark ? "text-white/60 group-hover:text-white" : "text-slate-400 group-hover:text-primary-600")} />
        </button>
      </div>
    </header>
  );
}
