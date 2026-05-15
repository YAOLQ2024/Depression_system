import { Home, MessageSquare, ClipboardList, Activity, Clock, User } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { cn } from "../lib/utils";
import { showProfileModal } from "./ProfileModal";

const NAV_ITEMS = [
  { label: "首页", icon: Home, path: "/" },
  { label: "问诊", icon: MessageSquare, path: "#" },
  { label: "量表", icon: ClipboardList, path: "#" },
  { label: "调节", icon: Activity, path: "#" },
  { label: "历史", icon: Clock, path: "#" },
];

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <aside className="w-56 lg:w-64 h-full flex flex-col pt-4 pb-8 glass-card border-none rounded-none rounded-r-3xl bg-gradient-to-b from-primary-50/50 to-white/30 backdrop-blur-xl relative overflow-hidden">
      {/* Decorative leaf background */}
      <div className="absolute -bottom-20 -left-20 w-64 h-64 bg-primary-100/40 rounded-full blur-3xl"></div>
      
      <nav className="flex-1 px-4 space-y-2 z-10 block">
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              className={cn(
                "w-full flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-300 font-medium text-[1.1rem]",
                isActive 
                  ? "bg-primary-500 text-white shadow-soft" 
                  : "text-slate-500 hover:bg-white/50 hover:text-primary-600"
              )}
            >
              <Icon className="w-6 h-6" />
              {item.label}
            </button>
          );
        })}
      </nav>
      
      <div className="px-4 mt-auto z-10">
        <div className="h-px w-full bg-slate-200/50 my-4"></div>
        <button
          onClick={showProfileModal}
          className="w-full flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all duration-300 font-medium text-[1.1rem] text-slate-500 hover:bg-white/50 hover:text-primary-600"
        >
          <User className="w-6 h-6" />
          我的账号
        </button>
      </div>

      {/* Decorative floral silhouette placeholder at bottom */}
      <div className="absolute bottom-0 left-0 right-0 px-6 z-0 opacity-30 pointer-events-none">
         <svg viewBox="0 0 100 100" className="w-full text-primary-500 fill-current opacity-20">
            <path d="M50 100 Q 20 50, 0 30 Q 30 20, 50 40 Q 70 20, 100 30 Q 80 50, 50 100 Z" />
         </svg>
      </div>
    </aside>
  );
}
