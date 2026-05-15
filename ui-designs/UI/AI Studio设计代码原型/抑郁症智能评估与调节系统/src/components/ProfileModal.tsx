import { useState, useEffect } from "react";
import { X, User, Settings, LogOut } from "lucide-react";

export const SHOW_PROFILE_MODAL_EVENT = "SHOW_PROFILE_MODAL_EVENT";
export function showProfileModal() {
  window.dispatchEvent(new Event(SHOW_PROFILE_MODAL_EVENT));
}

export function ProfileModal() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleShow = () => setIsOpen(true);
    window.addEventListener(SHOW_PROFILE_MODAL_EVENT, handleShow);
    return () => window.removeEventListener(SHOW_PROFILE_MODAL_EVENT, handleShow);
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm pointer-events-auto transition-opacity" 
        onClick={() => setIsOpen(false)}
      ></div>
      
      {/* Modal */}
      <div className="bg-white/80 backdrop-blur-2xl rounded-3xl shadow-glass border border-white/60 p-6 w-full max-w-sm pointer-events-auto relative scale-100 flex flex-col gap-6 animate-in fade-in zoom-in-95 duration-200">
        <button 
          onClick={() => setIsOpen(false)}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 bg-slate-100/50 hover:bg-slate-100 rounded-full transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
        
        <div className="flex flex-col items-center gap-3 pt-4">
          <img 
            src="https://images.unsplash.com/photo-1438761681033-6461ffad8d80?q=80&w=150&auto=format&fit=crop" 
            alt="用户头像" 
            className="w-20 h-20 rounded-full border-[3px] border-white shadow-sm object-cover"
          />
          <div className="text-center">
            <h3 className="text-xl font-bold text-slate-800">张三</h3>
            <p className="text-sm text-slate-500 mt-1">ID: UID_9527</p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
           <button className="flex items-center gap-3 p-3 rounded-xl hover:bg-white border border-transparent hover:border-white/80 transition-all font-medium text-slate-700">
             <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
               <User className="w-4 h-4" />
             </div>
             个人资料
           </button>
           <button className="flex items-center gap-3 p-3 rounded-xl hover:bg-white border border-transparent hover:border-white/80 transition-all font-medium text-slate-700">
             <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center text-purple-600">
               <Settings className="w-4 h-4" />
             </div>
             帐号设置
           </button>
           <div className="h-px w-full bg-slate-200/50 my-1"></div>
           <button className="flex items-center gap-3 p-3 rounded-xl hover:bg-red-50/50 border border-transparent hover:border-red-100 transition-all font-medium text-red-600">
             <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-600">
               <LogOut className="w-4 h-4 ml-1" />
             </div>
             退出登录
           </button>
        </div>
      </div>
    </div>
  );
}
