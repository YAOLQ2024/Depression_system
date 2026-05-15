import { Bell, ChevronDown } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { showProfileModal } from "./ProfileModal";
import { cn } from "../lib/utils";

interface HeaderProps {
  theme?: 'light' | 'dark';
  title?: string | null | false;
}

export function Header({ theme = 'light', title }: HeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const isDark = theme === 'dark';

  const handleLogoClick = () => {
    if (location.pathname !== "/") {
      navigate(-1);
    }
  };

  return (
    <header className="h-[48px] w-full flex items-center justify-between px-6 z-10 relative">
      <div className="flex items-center gap-3 cursor-pointer" onClick={handleLogoClick}>
        {/* Placeholder for Brain/AI Logo */}
        <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center text-white font-bold shadow-soft text-base">
          AI
        </div>
        <div>
          <h1 className={cn("text-base font-semibold leading-tight", isDark ? "text-white" : "text-slate-800")}>
            抑郁症数字人辅助评估系统 {title !== false && <span className={cn("text-[13px] font-normal ml-2", isDark ? "text-white/70" : "text-slate-500")}>{title || "量表问诊"}</span>}
          </h1>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <button className={cn("relative p-1.5 transition-colors", isDark ? "text-white/80 hover:text-white" : "text-slate-500 hover:text-primary-600")}>
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
          <span className="sr-only">消息</span>
        </button>
        
        <div 
          onClick={showProfileModal}
          className="flex items-center gap-2 cursor-pointer group hover:bg-white/10 p-1 md:pr-3 rounded-full transition-colors"
        >
          <img 
            src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?q=80&w=150&auto=format&fit=crop" 
            alt="用户头像" 
            className={cn("w-8 h-8 rounded-full border object-cover", isDark ? "border-white/20" : "border-slate-200")}
          />
          <span className={cn("text-sm font-medium transition-colors", isDark ? "text-white/90 group-hover:text-white" : "text-slate-700 group-hover:text-primary-600")}>张三</span>
          <ChevronDown className={cn("w-4 h-4 transition-colors", isDark ? "text-white/60 group-hover:text-white" : "text-slate-400 group-hover:text-primary-600")} />
        </div>
      </div>
    </header>
  );
}
