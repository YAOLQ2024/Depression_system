import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ConsultationLayout } from "../layouts";
import { mockConsultationService } from "../services/consultationService";
import { 
  User, 
  MapPin, 
  Ruler, 
  Weight, 
  Stethoscope, 
  Phone, 
  Edit3, 
  Check, 
  ArrowRight,
  ShieldAlert,
  Camera,
  Mic,
  Volume2,
  MonitorPlay,
  AlertCircle,
  X
} from "lucide-react";
import { cn } from "../lib/utils";

interface UserProfile {
  name: string;
  gender: string;
  age: string;
  height: string;
  weight: string;
  phone: string;
  department: string;
  occupation: string;
  hasPsychHistory: string;
  isMedicated: string;
}

export default function PreparationPage() {
  const navigate = useNavigate();
  // Simulate empty state initially
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Example state for authorizations
  const [isDeviceAuth, setIsDeviceAuth] = useState(false);
  const [isDataAuth, setIsDataAuth] = useState(false);
  // Fixed selection for demo
  const [isDoctorSelected, setIsDoctorSelected] = useState(false);

  const [formData, setFormData] = useState<Partial<UserProfile>>({
    name: "", gender: "男", age: "", height: "", weight: "", phone: "", department: "心理科", occupation: "学生", hasPsychHistory: "否", isMedicated: "否"
  });

  const isReady = profile !== null && isDeviceAuth && isDataAuth && isDoctorSelected;
  const readyCount = [profile !== null, isDeviceAuth, isDataAuth, isDoctorSelected].filter(Boolean).length;

  const handleStartConsultation = async () => {
    if (!isReady) return;
    try {
      const response = await mockConsultationService.startConsultation("user123");
      navigate("/consultation", { state: { sessionId: response.sessionId } });
    } catch (e) {
      console.error("Failed to start consultation", e);
    }
  };

  const handleSaveProfile = () => {
    setProfile(formData as UserProfile);
    setIsModalOpen(false);
  };

  return (
    <ConsultationLayout backgroundImage="./public/bg.webp" title="问诊准备">
      <div className="w-full h-full px-4 pt-2 pb-4 md:px-8 md:pt-2 md:pb-2 flex flex-col items-center z-10 text-white font-sans overflow-y-auto">
        
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-4 md:gap-6 mt-0">
          
          {/* Left Panel: Profile Info */}
          <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-[2rem] p-6 shadow-2xl relative overflow-hidden flex flex-col">
            <div className="absolute top-0 right-0 p-8 opacity-20 pointer-events-none">
               {/* Decorative brain icon or similar can go here */}
               <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/><path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/><path d="M6.002 6.5A3 3 0 0 1 5.602 5.125"/><path d="M11.8 21.2a1.2 1.2 0 0 0-1.183-1.18"/><path d="M13.383 20.02a1.2 1.2 0 0 0-1.183 1.18"/></svg>
            </div>
            
            <h2 className="text-3xl font-bold tracking-wider mb-2 z-10">信息录入</h2>
            <p className="text-white/60 text-sm mb-6 z-10">
              {profile ? "以下为您已填写的个人信息，请确认是否准确，如有错误可继续修改。" : "请先填写您的基础信息，以便我们为您提供更准确的评估。"}
            </p>

            {profile ? (
              <div className="grid grid-cols-2 gap-3 z-10">
                <InfoCard icon={<User className="w-5 h-5 text-blue-300" />} label="姓名" value={profile.name} className="col-span-2" />
                <InfoCard icon={<span className="text-xl leading-none text-blue-300">♂</span>} label="性别" value={profile.gender} />
                <InfoCard icon={<span className="text-xl leading-none text-blue-300">📅</span>} label="年龄" value={profile.age} />
                <InfoCard icon={<Ruler className="w-5 h-5 text-blue-300" />} label="身高" value={profile.height} />
                <InfoCard icon={<Weight className="w-5 h-5 text-blue-300" />} label="体重" value={profile.weight} />
                <InfoCard icon={<Stethoscope className="w-5 h-5 text-blue-300" />} label="科室" value={profile.department} />
                <InfoCard icon={<Phone className="w-5 h-5 text-blue-300" />} label="联系方式" value={profile.phone} />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center min-h-[300px] border-2 border-dashed border-white/20 rounded-2xl bg-white/5 z-10">
                <p className="text-white/50 text-sm">暂未填写信息</p>
              </div>
            )}

            <button 
              onClick={() => {
                if (profile) setFormData(profile);
                setIsModalOpen(true);
              }}
              className="mt-6 w-full py-4 rounded-full bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-white/30 hover:bg-white/10 transition-colors shadow-[0_0_15px_rgba(255,255,255,0.1)] flex items-center justify-center gap-2 group z-10"
            >
              <Edit3 className="w-5 h-5 group-hover:scale-110 transition-transform" />
              <span className="font-medium tracking-wide">{profile ? "修改信息" : "填写信息"}</span>
            </button>
          </div>

          {/* Right Panel: Checklists */}
          <div className="flex flex-col gap-4">
            
            {/* Step 1: Device Auth */}
            <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 relative overflow-hidden flex flex-col sm:flex-row gap-6 sm:items-center">
              <div className="text-4xl font-bold text-blue-400 opacity-60 absolute top-4 left-4">01</div>
              <div className="flex-1 pl-12">
                <div className="flex w-full justify-between items-center mb-1">
                  <h3 className="text-xl font-bold">设备与采集授权</h3>
                  <StatusBadge isDone={isDeviceAuth} textDone="已授权" textPending="待授权" />
                </div>
                <p className="text-white/60 text-sm mb-4">授权必要的设备与权限，保障问诊过程顺利进行</p>
                <div className="flex gap-4 sm:gap-8 justify-start">
                  <DeviceIcon icon={<Camera />} label="摄像头" />
                  <DeviceIcon icon={<Mic />} label="麦克风" />
                  <DeviceIcon icon={<Volume2 />} label="扬声器" />
                  <DeviceIcon icon={<MonitorPlay />} label="浏览器权限" />
                </div>
              </div>
              <div className="flex-shrink-0 mt-4 sm:mt-0">
                <button 
                  onClick={() => setIsDeviceAuth(true)}
                  disabled={isDeviceAuth}
                  className={cn("px-8 py-3 rounded-full font-medium transition-all", isDeviceAuth ? "bg-white/10 text-white/50 border border-white/10" : "bg-gradient-to-r from-purple-500 to-blue-600 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)]")}
                >
                  {isDeviceAuth ? "已完成授权" : "立即授权"}
                </button>
              </div>
            </div>

            {/* Step 2: Data Auth */}
            <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 relative overflow-hidden flex flex-col sm:flex-row gap-6 sm:items-center">
              <div className="text-4xl font-bold text-blue-400 opacity-60 absolute top-4 left-4">02</div>
              <div className="flex-1 pl-12">
                <div className="flex w-full justify-between items-center mb-1">
                  <h3 className="text-xl font-bold">数据采集说明与授权</h3>
                  <StatusBadge isDone={isDataAuth} textDone="已确认" textPending="待确认" />
                </div>
                <p className="text-white/60 text-sm mb-4">本次问诊将采集多维度数据，用于辅助评估</p>
                <div className="flex items-center gap-2 text-sm text-blue-200 bg-blue-500/10 w-fit px-3 py-1.5 rounded-full cursor-pointer hover:bg-blue-500/20 transition-colors">
                  <ShieldAlert className="w-4 h-4" />
                  <span>已阅读并同意本次数据采集说明</span>
                  <span className="text-blue-400 ml-2">查看详情 →</span>
                </div>
              </div>
              <div className="flex-shrink-0 mt-4 sm:mt-0">
                <button 
                  onClick={() => setIsDataAuth(true)}
                  disabled={isDataAuth}
                  className={cn("px-8 py-3 rounded-full font-medium transition-all", isDataAuth ? "bg-white/10 text-white/50 border border-white/10" : "bg-gradient-to-r from-purple-500 to-blue-600 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)]")}
                >
                  {isDataAuth ? "已同意" : "同意授权"}
                </button>
              </div>
            </div>

            {/* Step 3: Flow & Doctor */}
            <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 relative overflow-hidden flex flex-col md:flex-row gap-6">
              <div className="text-4xl font-bold text-blue-400 opacity-60 absolute top-4 left-4">03</div>
              <div className="flex-1 pl-12">
                <div className="flex w-full justify-between items-center mb-1">
                  <h3 className="text-xl font-bold">问诊流程与医生选择</h3>
                  <StatusBadge isDone={isDoctorSelected} textDone="已选择" textPending="待选择" />
                </div>
                <p className="text-white/60 text-sm mb-4">了解问诊流程，选择合适的询诊风格</p>
                
                <div className="flex items-center gap-2 mb-2 text-sm text-white/80 flex-wrap">
                  <div className="bg-blue-500/20 px-3 py-1.5 rounded-lg flex flex-col min-w-[120px]">
                     <span className="text-blue-300 font-medium mb-1">❶ 基础问答</span>
                     <span className="text-xs text-white/50">了解基本情况</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-white/30" />
                  <div className="bg-blue-500/20 px-3 py-1.5 rounded-lg flex flex-col min-w-[120px]">
                     <span className="text-blue-300 font-medium mb-1">❷ 量表评估</span>
                     <span className="text-xs text-white/50">PHQ-9/SDQ/SAS<br/>社会功能量表</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-white/30" />
                  <div className="bg-blue-500/20 px-3 py-1.5 rounded-lg flex flex-col min-w-[120px]">
                     <span className="text-blue-300 font-medium mb-1">❸ 综合分析</span>
                     <span className="text-xs text-white/50">生成评估报告<br/>与调节建议</span>
                  </div>
                </div>
              </div>

              <div 
                onClick={() => setIsDoctorSelected(true)}
                className={cn("bg-white/5 border rounded-2xl p-4 flex gap-4 items-center shrink-0 w-full sm:w-auto mt-4 md:mt-0 transition-all cursor-pointer", isDoctorSelected ? "border-blue-400 ring-2 ring-blue-500/50" : "border-white/10 hover:border-white/30")}
              >
                <img 
                  src="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?q=80&w=200&auto=format&fit=crop" 
                  alt="Doctor" 
                  className="w-14 h-14 rounded-full object-cover border-2 border-blue-400/50"
                />
                <div className="flex flex-col">
                  <div className="font-bold text-lg">温和陪伴型</div>
                  <div className="text-white/60 text-xs mb-1">耐心倾听，温和引导</div>
                  <div className="text-blue-400 text-xs text-left">
                    更换风格 →
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* Bottom Actions */}
        <div className="w-full max-w-6xl mt-auto pt-6 pb-2 md:pb-4 flex flex-col sm:flex-row justify-center sm:justify-between items-center gap-6">
           <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/10 flex items-center gap-4">
             <div className="bg-blue-500/20 p-2 rounded-lg"><Check className="w-5 h-5 text-blue-400" /></div>
             <div>
               <div className="text-sm font-medium flex gap-2">准备状态 <span className="text-blue-400">{readyCount}/4</span> {readyCount === 4 ? <span className="text-green-400">已完成</span> : <span className="text-orange-400">进行中</span>}</div>
               <div className="w-48 h-1 bg-white/10 rounded-full mt-2 overflow-hidden">
                 <div className="h-full bg-gradient-to-r from-blue-400 to-purple-500 transition-all duration-500" style={{ width: `${(readyCount/4)*100}%` }}></div>
               </div>
             </div>
             <p className="text-xs text-white/50 ml-4 hidden md:block">完成全部准备后即可开始问诊</p>
           </div>

           <button 
             onClick={handleStartConsultation}
             disabled={!isReady}
             className={cn(
               "px-12 py-4 rounded-full font-bold text-xl flex items-center gap-2 transition-all duration-300",
               isReady 
                 ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 shadow-[0_0_30px_rgba(79,70,229,0.5)] hover:shadow-[0_0_40px_rgba(79,70,229,0.7)] hover:scale-105" 
                 : "bg-white/10 text-white/40 border border-white/10 cursor-not-allowed"
             )}
           >
             进入数字人问诊 <ArrowRight className="w-6 h-6" />
           </button>

           <div className="bg-white/5 backdrop-blur-md rounded-2xl p-4 border border-white/10 flex items-center gap-3 hidden lg:flex max-w-[280px]">
             <ShieldAlert className="w-8 h-8 text-blue-300/60" />
             <p className="text-xs text-white/50 leading-tight">问诊过程中可能暂时存储数据，我们将保护您的隐私安全。</p>
           </div>
        </div>

      </div>

      {/* Info Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col font-sans animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-6 pb-2 border-b border-slate-100">
              <div>
                <h2 className="text-2xl font-bold text-slate-800">信息录入</h2>
                <p className="text-sm text-slate-500">请补充或修改以下基础信息，用于本次问诊评估。</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[60vh] space-y-6">
               <div>
                 <h3 className="flex items-center gap-2 text-sm font-bold text-teal-600 px-3 py-1 bg-teal-50 w-fit rounded-full mb-4">
                   <div className="w-1.5 h-4 bg-teal-500 rounded-full"></div>
                   基础信息
                 </h3>
                 <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                   <InputField label="1. 姓名/昵称" value={formData.name || ''} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="张三" icon={<User className="w-4 h-4" />} />
                   <div className="flex flex-col gap-1.5">
                     <label className="text-sm font-medium text-slate-700 flex items-center gap-2"><span className="text-teal-600">♂</span> 2. 性别</label>
                     <select value={formData.gender || '男'} onChange={e => setFormData({...formData, gender: e.target.value})} className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all">
                       <option>男</option>
                       <option>女</option>
                       <option>保密</option>
                     </select>
                   </div>
                   <InputField label="3. 年龄" value={formData.age || ''} onChange={e => setFormData({...formData, age: e.target.value})} placeholder="24" type="number" icon={<span className="text-slate-400 text-xs">📅</span>} />
                   <InputField label="4. 身高" value={formData.height || ''} onChange={e => setFormData({...formData, height: e.target.value})} placeholder="175" append="cm" icon={<Ruler className="w-4 h-4" />} />
                   <InputField label="5. 体重" value={formData.weight || ''} onChange={e => setFormData({...formData, weight: e.target.value})} placeholder="68" append="kg" icon={<Weight className="w-4 h-4" />} />
                   <InputField label="6. 手机号" value={formData.phone || ''} onChange={e => setFormData({...formData, phone: e.target.value})} placeholder="138****1234" icon={<Phone className="w-4 h-4" />} />
                   <div className="flex flex-col gap-1.5 sm:col-span-2 md:col-span-1">
                     <label className="text-sm font-medium text-slate-700 flex items-center gap-2"><Stethoscope className="w-4 h-4 text-slate-400" /> 7. 职业/身份</label>
                     <select value={formData.occupation || '学生'} onChange={e => setFormData({...formData, occupation: e.target.value})} className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-teal-500 focus:border-transparent outline-none transition-all">
                       <option>学生</option>
                       <option>在职</option>
                       <option>自由职业</option>
                       <option>待业</option>
                     </select>
                   </div>
                 </div>
               </div>

               <div>
                 <h3 className="flex items-center gap-2 text-sm font-bold text-teal-600 px-3 py-1 bg-teal-50 w-fit rounded-full mb-4">
                   <div className="w-1.5 h-4 bg-teal-500 rounded-full"></div>
                   心理相关信息
                 </h3>
                 <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                   <div className="flex flex-col gap-2">
                     <label className="text-sm font-medium text-slate-700 flex items-center gap-2"><span className="text-teal-600">♡</span> 8. 是否曾因心理/精神问题就诊</label>
                     <div className="flex bg-slate-100 rounded-xl p-1 gap-1">
                       {['否', '是', '不确定'].map(opt => (
                         <button key={opt} onClick={() => setFormData({...formData, hasPsychHistory: opt})} className={cn("flex-1 py-2 text-sm font-medium rounded-lg transition-colors", formData.hasPsychHistory === opt ? "bg-white text-teal-600 shadow-sm" : "text-slate-500 hover:text-slate-700")}>{opt}</button>
                       ))}
                     </div>
                   </div>
                   <div className="flex flex-col gap-2">
                     <label className="text-sm font-medium text-slate-700 flex items-center gap-2"><Check className="w-4 h-4 text-teal-600" /> 9. 当前是否服药</label>
                     <div className="flex bg-slate-100 rounded-xl p-1 gap-1">
                       {['否', '是', '不确定'].map(opt => (
                         <button key={opt} onClick={() => setFormData({...formData, isMedicated: opt})} className={cn("flex-1 py-2 text-sm font-medium rounded-lg transition-colors", formData.isMedicated === opt ? "bg-white text-teal-600 shadow-sm" : "text-slate-500 hover:text-slate-700")}>{opt}</button>
                       ))}
                     </div>
                   </div>
                 </div>
               </div>
            </div>

            <div className="p-6 border-t border-slate-100 flex gap-4 justify-center sm:justify-end bg-slate-50/50">
              <button onClick={() => setIsModalOpen(false)} className="px-8 py-3 rounded-full font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 transition-colors hidden sm:block">取消</button>
              <button 
                onClick={handleSaveProfile}
                className="w-full sm:w-auto px-10 py-3 rounded-full font-medium text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:shadow-lg transition-all"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}

    </ConsultationLayout>
  );
}

function StatusBadge({ isDone, textDone, textPending }: { isDone: boolean, textDone: string, textPending: string }) {
  if (isDone) {
    return <span className="bg-green-500/20 text-green-400 px-3 py-1 text-xs rounded-full border border-green-500/30 flex items-center gap-1"><Check className="w-3 h-3" /> {textDone}</span>;
  }
  return <span className="bg-orange-500/20 text-orange-400 px-3 py-1 text-xs rounded-full border border-orange-500/30 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> {textPending}</span>;
}

function DeviceIcon({ icon, label }: { icon: React.ReactNode, label: string }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="text-green-400 bg-green-400/10 p-2 rounded-lg">{icon}</div>
      <span className="text-xs text-white/70">{label}</span>
    </div>
  );
}

function InfoCard({ icon, label, value, className }: { icon: React.ReactNode, label: string, value: string, className?: string }) {
  return (
    <div className={cn("bg-white/5 border border-white/10 rounded-xl p-3 flex items-center gap-3", className)}>
      <div className="bg-blue-500/20 p-2 rounded-lg text-white">
        {icon}
      </div>
      <div className="flex flex-col">
        <span className="text-xs text-secondary-300">{label}</span>
        <span className="text-sm font-medium truncate">{value}</span>
      </div>
    </div>
  );
}

function InputField({ label, value, onChange, placeholder, append, type = "text", icon }: any) {
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
