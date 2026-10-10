import { useEffect, useRef, useState } from "react";
import { Bell, ChevronDown, CircleAlert } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useNavigate, useLocation } from "react-router-dom";
import { showProfileModal } from "./ProfileModal";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { getProfileStatusLabel, getUserDisplayName, getUserInitial } from "../lib/account";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";
import {
  getSystemNotifications,
  markSystemNotificationsRead,
  subscribeSystemNotifications,
  type SystemNotification,
} from "../lib/systemNotifications";

interface HeaderProps {
  theme?: 'light' | 'dark';
  title?: string | null | false;
}

function formatNotificationTime(createdAt: number) {
  const elapsed = Date.now() - createdAt;
  if (elapsed < 60_000) return "刚刚";
  if (elapsed < 3_600_000) return `${Math.floor(elapsed / 60_000)} 分钟前`;
  return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit" }).format(createdAt);
}

function NotificationItem({ notification, isDark }: { notification: SystemNotification; isDark: boolean }) {
  return (
    <div className={cn("rounded-xl border px-3 py-2.5", isDark ? "border-rose-300/15 bg-rose-400/10" : "border-rose-100 bg-rose-50/80")}>
      <div className="flex items-start gap-2.5">
        <CircleAlert className={cn("mt-0.5 h-4 w-4 shrink-0", isDark ? "text-rose-300" : "text-rose-500")} />
        <div className="min-w-0 flex-1">
          <p className={cn("break-words text-xs font-medium leading-5", isDark ? "text-rose-100" : "text-rose-700")}>{notification.message}</p>
          <p className={cn("mt-1 text-[10px]", isDark ? "text-white/45" : "text-slate-400")}>{formatNotificationTime(notification.createdAt)}</p>
        </div>
      </div>
    </div>
  );
}

export function Header({ theme = 'light', title }: HeaderProps) {
  const { state } = useConsultationAppContext();
  const navigate = useNavigate();
  const location = useLocation();
  const isDark = theme === 'dark';
  const userDisplayName = getUserDisplayName(state.user);
  const profileStatusLabel = getProfileStatusLabel(state.user?.profile_status);
  const userInitial = getUserInitial(state.user);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<SystemNotification[]>(() => getSystemNotifications());
  const notificationsRef = useRef<HTMLDivElement | null>(null);
  const unreadCount = notifications.filter((notification) => !notification.read).length;

  useEffect(() => subscribeSystemNotifications(() => setNotifications(getSystemNotifications())), []);

  useEffect(() => {
    if (!showNotifications) {
      return undefined;
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node) || !notificationsRef.current?.contains(target)) {
        setShowNotifications(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowNotifications(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    window.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [showNotifications]);

  const handleLogoClick = () => {
    if (location.pathname !== APP_PATHS.home) {
      navigate(APP_PATHS.home);
    }
  };

  return (
    <header className="app-header relative z-10 flex h-[clamp(56px,4.2vw,88px)] w-full items-center justify-between px-[clamp(12px,1.25vw,30px)]">
      <div className="header-brand flex min-w-0 -translate-y-[clamp(6px,0.55vw,12px)] cursor-pointer items-center gap-[clamp(8px,0.7vw,16px)]" onClick={handleLogoClick}>
        <div className="header-logo h-[clamp(28px,2.2vw,48px)] w-[clamp(58px,4vw,84px)] shrink-0 overflow-hidden">
          <img
            src="/aim-brand-lockup-transparent-clean.png"
            alt="AIM"
            className="h-full w-auto max-w-none object-contain object-left drop-shadow-[0_1px_4px_rgba(255,255,255,0.16)]"
          />
        </div>
        <div className="header-titles flex min-w-0 items-center gap-[clamp(8px,0.7vw,16px)]">
          <h1 className={cn("header-system-title shrink-0 text-[clamp(14px,1.05vw,24px)] font-semibold leading-tight", isDark ? "text-white" : "text-slate-800")}>
            抑郁症数字人辅助评估系统
          </h1>
          {title !== false ? (
            <div className="header-page-title flex min-w-0 items-center gap-[clamp(8px,0.7vw,16px)]">
              <span className={cn("h-[clamp(16px,1.25vw,28px)] w-px rounded-full", isDark ? "bg-white/20" : "bg-slate-300")} />
              <span className={cn("truncate text-[clamp(12px,0.85vw,19px)] font-normal", isDark ? "text-white/70" : "text-slate-500")}>
                {title || "量表问诊"}
              </span>
            </div>
          ) : null}
        </div>
      </div>
      
      <div className="header-account flex -translate-y-[clamp(6px,0.55vw,12px)] items-center gap-[clamp(10px,1vw,24px)]">
        <div ref={notificationsRef} className="header-notifications relative">
          <button
            type="button"
            onClick={() => {
              const nextOpen = !showNotifications;
              setShowNotifications(nextOpen);
              if (nextOpen) markSystemNotificationsRead();
            }}
            className={cn("relative rounded-xl p-[clamp(5px,0.4vw,10px)] transition-colors", isDark ? "text-white/70 hover:bg-white/10 hover:text-white" : "text-slate-500 hover:bg-white/70 hover:text-primary-600")}
            aria-expanded={showNotifications}
            aria-label="打开系统消息中心"
          >
            <Bell className="h-[clamp(18px,1.35vw,30px)] w-[clamp(18px,1.35vw,30px)]" />
            {unreadCount > 0 ? <span className="absolute right-[clamp(3px,0.2vw,5px)] top-[clamp(3px,0.2vw,5px)] h-2.5 w-2.5 rounded-full border-2 border-white bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.85)]" /> : null}
          </button>

          <AnimatePresence>
            {showNotifications ? (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -5, scale: 0.98 }}
                transition={{ duration: 0.16, ease: "easeOut" }}
                className={cn("absolute right-0 top-full z-[120] mt-2 w-[min(360px,calc(100vw-32px))] overflow-hidden rounded-2xl border p-3 shadow-[0_22px_48px_rgba(15,23,42,0.24)] backdrop-blur-xl", isDark ? "border-white/20 bg-slate-950/90" : "border-white/80 bg-white/94")}
              >
                <div className={cn("flex items-center justify-between border-b px-1 pb-2.5", isDark ? "border-white/10" : "border-slate-100")}>
                  <div>
                    <p className={cn("text-sm font-semibold", isDark ? "text-white" : "text-slate-800")}>系统消息</p>
                  </div>
                  <span className={cn("rounded-full px-2 py-1 text-[10px] font-semibold", isDark ? "bg-white/10 text-white/70" : "bg-slate-100 text-slate-500")}>{notifications.length} 条</span>
                </div>
                <div
                  className="notification-list mt-2.5 max-h-[min(18rem,calc(100dvh-10rem))] space-y-2 overflow-x-hidden overflow-y-scroll overscroll-y-contain pr-2"
                  data-theme={isDark ? "dark" : "light"}
                  role="region"
                  aria-label="系统消息列表"
                  tabIndex={0}
                >
                  {notifications.length ? notifications.map((notification) => <NotificationItem key={notification.id} notification={notification} isDark={isDark} />) : (
                    <div className={cn("rounded-xl border border-dashed px-3 py-6 text-center text-xs", isDark ? "border-white/15 text-white/45" : "border-slate-200 text-slate-400")}>暂无运行异常消息</div>
                  )}
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
        
        <button
          type="button"
          onClick={(event) => {
            setShowNotifications(false);
            showProfileModal(event.currentTarget);
          }}
          aria-label="打开账号菜单"
          aria-haspopup="menu"
          className="header-profile-button group flex cursor-pointer items-center gap-[clamp(7px,0.6vw,14px)] rounded-full p-[clamp(4px,0.35vw,8px)] transition-colors hover:bg-white/10 md:pr-[clamp(10px,0.9vw,20px)]"
        >
          <div
            className={cn(
              "header-avatar flex h-[clamp(30px,2.25vw,50px)] w-[clamp(30px,2.25vw,50px)] items-center justify-center rounded-full border text-[clamp(13px,0.95vw,21px)] font-semibold shadow-sm",
              isDark ? "border-white/20 bg-white/10 text-white" : "border-slate-200 bg-primary-50 text-primary-700",
            )}
          >
            {userInitial}
          </div>
          <div className="header-user-info hidden md:flex flex-col items-start leading-tight">
            <span className={cn("text-[clamp(13px,0.95vw,21px)] font-medium transition-colors", isDark ? "text-white/90 group-hover:text-white" : "text-slate-700 group-hover:text-primary-600")}>
              {userDisplayName}
            </span>
            <span className={cn("text-[clamp(10px,0.7vw,15px)]", isDark ? "text-white/60 group-hover:text-white/80" : "text-slate-400 group-hover:text-slate-500")}>
              {profileStatusLabel}
            </span>
          </div>
          <ChevronDown className={cn("header-profile-chevron h-[clamp(15px,1.1vw,24px)] w-[clamp(15px,1.1vw,24px)] transition-colors", isDark ? "text-white/60 group-hover:text-white" : "text-slate-400 group-hover:text-primary-600")} />
        </button>
      </div>
    </header>
  );
}
