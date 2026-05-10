import React, { useState } from 'react';
import { Shield, Lock, User, Eye, EyeOff, LayoutTemplate, Activity, History, Heart } from 'lucide-react';
import { motion } from 'motion/react';

interface AuthPageProps {
  onLogin: () => void;
}

const AuthPage: React.FC<AuthPageProps> = ({ onLogin }) => {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');
  const [showPassword, setShowPassword] = useState(false);

  const features = [
    { title: '快速测评', icon: LayoutTemplate, desc: '基于专业量表，3-5分钟快速评估' },
    { title: '趋势追踪', icon: Activity, desc: '可视化情绪曲线，见证康复历程' },
    { title: '多模态辅助', icon: History, desc: '整合语音、表情、生理多维数据' },
    { title: '私密安全', icon: Shield, desc: '医疗级加密，全方位保护用户隐私' },
  ];

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6 relative overflow-hidden">
      <div className="max-w-[1200px] w-full grid grid-cols-1 lg:grid-cols-2 gap-12 z-10">
        {/* Left: Brand Section */}
        <div className="flex flex-col justify-center">
          <div className="mb-10 inline-flex items-center gap-3">
             <div className="w-12 h-12 bg-[#0F6BFF] rounded-2xl flex items-center justify-center shadow-xl shadow-blue-600/30">
               <Heart className="text-white" size={24} fill="currentColor" />
             </div>
             <div>
               <div className="text-2xl font-bold text-[#172033]">SDS System</div>
               <div className="text-[10px] text-[#6B7893] tracking-[4px] uppercase font-semibold">Mental Health Care</div>
             </div>
          </div>

          <div className="mb-8">
            <span className="inline-block px-3 py-1 bg-[#EAF3FF] text-[#0F6BFF] text-xs font-bold rounded-full mb-4 shadow-[0_4px_12px_rgba(15,107,255,0.15)] italic uppercase tracking-wider">
              Professional Assessment
            </span>
            <h1 className="text-5xl lg:text-6xl font-extrabold text-[#172033] leading-tight mb-4">
              探索内心，<br />
              <span className="text-[#0F6BFF]">重获平静的力量。</span>
            </h1>
            <p className="text-[#6B7893] text-lg max-w-md leading-relaxed">
              融合专业量表与多模态数据，3-5分钟生成可解释的心理健康建议，全流程隐私加密。
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {features.map((f, i) => (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                key={f.title} 
                className="p-5 rounded-3xl bg-white/50 backdrop-blur-sm border border-white hover:bg-white hover:shadow-xl hover:shadow-blue-900/5 transition-all cursor-default"
              >
                <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center text-[#0F6BFF] mb-3 shadow-md border border-blue-50">
                  <f.icon size={20} />
                </div>
                <h3 className="font-bold text-[#172033] mb-1">{f.title}</h3>
                <p className="text-xs text-[#6B7893] leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-12 flex gap-4">
             <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/40 border border-white/60 text-[10px] text-[#6B7893] font-medium backdrop-blur-md">
                <Shield size={14} className="text-emerald-500" />
                数据隐私保护
             </div>
             <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/40 border border-white/60 text-[10px] text-[#6B7893] font-medium backdrop-blur-md">
                <Lock size={14} className="text-blue-500" />
                仅供参考，非医疗诊断
             </div>
          </div>
        </div>

        {/* Right: Login Card */}
        <div className="flex items-center justify-center lg:justify-end">
          <motion.div 
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
            className="w-full max-w-[480px] bg-white/70 backdrop-blur-2xl rounded-[40px] p-10 shadow-[0_20px_50px_rgba(0,0,0,0.05)] border border-white relative"
          >
             {/* Card Pattern Overlay */}
             <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
                  style={{ backgroundImage: 'radial-gradient(#000 1px, transparent 0)', backgroundSize: '24px 24px' }} />

             <div className="relative z-10">
               <div className="mb-10">
                 <h2 className="text-3xl font-bold text-[#172033] mb-2">
                   {activeTab === 'login' ? '欢迎回来' : '开启您的心理之旅'}
                 </h2>
                 <p className="text-[#6B7893] text-sm">
                   {activeTab === 'login' ? '请输入您的账号以继续。' : '建立您的健康档案，开始专业测评。'}
                 </p>
               </div>

               <div className="flex bg-gray-100/50 p-1 rounded-2xl mb-8">
                 <button 
                  onClick={() => setActiveTab('login')}
                  className={`flex-1 py-3 text-sm font-bold rounded-xl transition-all ${activeTab === 'login' ? 'bg-white text-[#0F6BFF] shadow-sm' : 'text-[#6B7893]'}`}
                 >
                   登录
                 </button>
                 <button 
                  onClick={() => setActiveTab('register')}
                  className={`flex-1 py-3 text-sm font-bold rounded-xl transition-all ${activeTab === 'register' ? 'bg-white text-[#0F6BFF] shadow-sm' : 'text-[#6B7893]'}`}
                 >
                   注册
                 </button>
               </div>

               <form className="space-y-6" onSubmit={(e) => { e.preventDefault(); onLogin(); }}>
                 {activeTab === 'register' && (
                   <div className="space-y-2">
                     <label className="text-sm font-bold text-[#172033] ml-1">姓名</label>
                     <div className="relative">
                       <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
                       <input 
                        type="text" 
                        required
                        placeholder="您的真实姓名" 
                        className="w-full h-14 pl-12 pr-4 bg-white/80 border border-[#E6EEFB] rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-[#0F6BFF] outline-none transition-all placeholder:text-[#6B7893]/50" 
                       />
                     </div>
                   </div>
                 )}

                 <div className="space-y-2">
                   <label className="text-sm font-bold text-[#172033] ml-1">账号</label>
                   <div className="relative">
                     <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
                     <input 
                      type="text" 
                      required
                      placeholder="用户名 / 手机号" 
                      className="w-full h-14 pl-12 pr-4 bg-white/80 border border-[#E6EEFB] rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-[#0F6BFF] outline-none transition-all placeholder:text-[#6B7893]/50" 
                     />
                   </div>
                 </div>

                 <div className="space-y-2">
                   <div className="flex justify-between items-center px-1">
                     <label className="text-sm font-bold text-[#172033]">密码</label>
                     {activeTab === 'login' && <button type="button" className="text-[10px] font-bold text-[#0F6BFF] hover:underline">忘记密码?</button>}
                   </div>
                   <div className="relative">
                     <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6B7893]" />
                     <input 
                      type={showPassword ? 'text' : 'password'} 
                      required
                      placeholder="请输入密码" 
                      className="w-full h-14 pl-12 pr-12 bg-white/80 border border-[#E6EEFB] rounded-2xl focus:ring-4 focus:ring-blue-100 focus:border-[#0F6BFF] outline-none transition-all placeholder:text-[#6B7893]/50" 
                     />
                     <button 
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-[#6B7893] hover:text-[#0F6BFF] transition-colors"
                     >
                       {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                     </button>
                   </div>
                 </div>

                 {activeTab === 'login' && (
                   <div className="flex items-center gap-2 px-1">
                     <input type="checkbox" id="remember" className="w-4 h-4 rounded border-[#E6EEFB] text-[#0F6BFF] focus:ring-[#0F6BFF]" />
                     <label htmlFor="remember" className="text-xs text-[#6B7893] font-medium">30天内自动登录</label>
                   </div>
                 )}

                 <button 
                  type="submit"
                  className="w-full h-14 bg-[#0F6BFF] hover:bg-[#0A4BB3] text-white font-bold rounded-2xl shadow-[0_10px_25px_rgba(15,107,255,0.3)] hover:shadow-none transform hover:scale-[0.98] transition-all active:scale-95 flex items-center justify-center gap-2"
                 >
                   {activeTab === 'login' ? '登 录' : '立 即 注 册'}
                 </button>

                 <div className="text-center mt-6">
                   <p className="text-xs text-[#6B7893]">
                     {activeTab === 'login' ? '还没有账号？' : '已有账号？'}
                     <button 
                      type="button" 
                      onClick={() => setActiveTab(activeTab === 'login' ? 'register' : 'login')}
                      className="text-[#0F6BFF] font-bold ml-1 hover:underline outline-none"
                     >
                       {activeTab === 'login' ? '立即注册' : '返回登录'}
                     </button>
                   </p>
                 </div>
               </form>
             </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
