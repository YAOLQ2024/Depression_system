import { useNavigate } from "react-router-dom";
import { MessageCircle, ClipboardList, Leaf, User, MessageSquare, Plus, Star } from "lucide-react";
import { Header } from "../components/Header";

export default function HomePage() {
  const navigate = useNavigate();

  const handleStartConsultation = () => {
    navigate("/preparation");
  };

  return (
    <div className="h-screen w-full flex flex-col font-sans overflow-hidden bg-[#9eaaf5] relative z-0">
      {/* Background Layer mimicking the purple futuristic style */}
      <div className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat opacity-40 mix-blend-overlay" style={{ backgroundImage: "url('/bg.png')" }} />
      <div className="absolute inset-0 z-0 bg-gradient-to-br from-indigo-500/30 via-purple-400/20 to-blue-400/30" />
      
      {/* Light spots and glowing effects */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-300/30 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute top-[20%] right-[-10%] w-[60%] h-[60%] bg-purple-400/20 blur-[150px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] left-[20%] w-[50%] h-[50%] bg-indigo-500/20 blur-[130px] rounded-full pointer-events-none" />
      
      {/* Top Header */}
      <div className="relative z-20 w-full">
        <Header theme="dark" title="首页" />
      </div>

      <main className="flex-1 relative flex z-10 overflow-hidden w-full max-w-[1440px] mx-auto">
        {/* Left Side: Digital Human Image */}
        <div className="absolute left-0 bottom-0 w-[45%] h-[90%] md:h-[95%] lg:h-[105%] flex items-end justify-center pointer-events-none z-20 xl:left-[2%]">
          <img 
            src="/SZR.png" 
            alt="AI Digital Human" 
            className="w-auto h-full object-contain object-bottom scale-x-[-1] md:scale-x-100" // Might need scale-x-[-1] depending on SZR.png orientation, but left it standard. Actually looking at the mock it's facing right. Let's just render normally.
          />
        </div>

        {/* Right Side: Interface Panel */}
        <div 
          className="absolute right-4 md:right-12 lg:right-24 xl:right-[8%] top-[10%] bottom-[5%] w-[90%] md:w-[50%] max-w-[640px] flex flex-col justify-center z-30 pointer-events-none"
          style={{ containerType: 'inline-size' }}
        >
          <div className="pointer-events-auto">
            
            {/* Glass Container for UI */}
            <div className="bg-white/10 backdrop-blur-3xl border border-white/30 rounded-[clamp(24px,6cqw,40px)] p-[clamp(24px,6cqw,48px)] shadow-[0_20px_50px_rgba(30,20,80,0.1)] relative overflow-hidden">
               {/* Inner glow */}
               <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent pointer-events-none opacity-50" />
               <div className="absolute top-0 right-0 w-64 h-64 bg-white/20 blur-[80px] rounded-full pointer-events-none" />

               <div className="relative z-10 flex flex-col gap-[clamp(16px,4cqw,32px)]">
                  {/* Greeting Text */}
                  <div className="text-white">
                    <h2 className="text-[clamp(24px,6cqw,48px)] font-medium tracking-tight mb-[clamp(8px,2cqw,12px)] drop-shadow-md leading-tight">
                      您好，张三
                    </h2>
                    <p className="text-white/80 text-[clamp(14px,3cqw,20px)] font-light tracking-wide">
                      我将协助您完成心理状态评估
                    </p>
                  </div>

                  {/* Big CTA Button */}
                  <button 
                    onClick={handleStartConsultation}
                    className="w-full relative group overflow-hidden rounded-[clamp(20px,4cqw,32px)] p-[2px] transition-transform duration-300 hover:scale-[1.02] active:scale-[0.98]"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-500 rounded-[clamp(20px,4cqw,32px)] opacity-80 group-hover:opacity-100 transition-opacity" />
                    
                    {/* Shimmer effect */}
                    <div className="absolute inset-0 z-10 overflow-hidden rounded-[clamp(20px,4cqw,32px)] pointer-events-none">
                      <div className="absolute top-0 -left-[100%] w-1/2 h-full block transform skew-x-[-20deg] bg-gradient-to-r from-transparent via-white/40 to-transparent group-hover:left-[200%] transition-all duration-1000 ease-in-out" />
                    </div>

                    <div className="relative z-20 bg-gradient-to-r from-blue-500/40 to-purple-600/40 backdrop-blur-xl rounded-[clamp(18px,4cqw,30px)] px-[clamp(16px,4cqw,32px)] py-[clamp(16px,3.5cqw,24px)] flex items-center justify-between border border-white/40 shadow-inner">
                      
                      {/* Sparkles inside button */}
                      <div className="absolute top-[20%] left-[30%] w-1 h-1 bg-white rounded-full shadow-[0_0_8px_2px_#fff] animate-pulse" style={{ animationDuration: '2s' }} />
                      <div className="absolute bottom-[30%] right-[15%] w-1.5 h-1.5 bg-blue-100 rounded-full shadow-[0_0_12px_2px_#bfdbfe] animate-pulse" style={{ animationDelay: '500ms', animationDuration: '3s' }} />
                      <div className="absolute top-[40%] right-[35%] w-2 h-2 bg-purple-200/80 rounded-full shadow-[0_0_15px_3px_#e9d5ff] animate-pulse" style={{ animationDelay: '1000ms', animationDuration: '2.5s' }} />

                      <div className="flex items-center gap-[clamp(12px,2.5cqw,16px)]">
                        <div className="w-[clamp(40px,8cqw,56px)] h-[clamp(40px,8cqw,56px)] bg-white rounded-full flex items-center justify-center shadow-lg shrink-0">
                          <MessageCircle className="w-[clamp(24px,4cqw,28px)] h-[clamp(24px,4cqw,28px)] text-indigo-600" fill="currentColor" />
                        </div>
                        <span className="text-[clamp(20px,4.5cqw,30px)] font-semibold text-white tracking-widest pl-2 drop-shadow-md truncate">开始问诊</span>
                      </div>
                      <div className="w-[clamp(32px,6cqw,48px)] h-[clamp(32px,6cqw,48px)] rounded-full border border-white/50 flex items-center justify-center text-white bg-white/10 group-hover:bg-white/20 transition-colors shrink-0">
                        <svg className="w-[clamp(20px,4cqw,24px)] h-[clamp(20px,4cqw,24px)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                        </svg>
                      </div>
                    </div>
                  </button>

                  {/* 2x2 Grid Buttons */}
                  <div className="grid grid-cols-2 gap-[clamp(12px,3cqw,24px)]">
                    <button className="relative overflow-hidden flex justify-between items-center bg-white/10 hover:bg-white/20 backdrop-blur-lg border border-white/40 rounded-[clamp(16px,4cqw,24px)] p-[clamp(16px,3cqw,20px)] transition-all duration-300 hover:-translate-y-1 group">
                      <div className="absolute top-0 -left-[100%] w-[120%] h-full block transform skew-x-[-20deg] bg-gradient-to-r from-transparent via-white/20 to-transparent group-hover:left-[200%] transition-all duration-700 ease-in-out pointer-events-none" />
                      <div className="relative z-10 flex items-center gap-[clamp(12px,3cqw,16px)] overflow-hidden">
                        <div className="w-[clamp(40px,8cqw,56px)] h-[clamp(40px,8cqw,56px)] shrink-0 rounded-[clamp(12px,2.5cqw,16px)] bg-gradient-to-br from-blue-400 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
                          <ClipboardList className="w-[clamp(24px,4cqw,28px)] h-[clamp(24px,4cqw,28px)]" />
                        </div>
                        <div className="flex flex-col items-start min-w-0 pr-2">
                          <span className="text-white text-[clamp(14px,3cqw,18px)] font-semibold tracking-wide truncate w-full text-left">历史记录</span>
                          <span className="text-white/60 text-[clamp(12px,2cqw,14px)] mt-0.5 truncate w-full text-left">评估记录</span>
                        </div>
                      </div>
                      <div className="relative z-10 w-[clamp(24px,4cqw,32px)] h-[clamp(24px,4cqw,32px)] shrink-0 rounded-full border border-white/30 flex items-center justify-center text-white/70 group-hover:text-white group-hover:border-white/60 transition-colors">
                        <svg className="w-[clamp(12px,2cqw,16px)] h-[clamp(12px,2cqw,16px)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </button>

                    <button className="relative overflow-hidden flex justify-between items-center bg-white/10 hover:bg-white/20 backdrop-blur-lg border border-white/40 rounded-[clamp(16px,4cqw,24px)] p-[clamp(16px,3cqw,20px)] transition-all duration-300 hover:-translate-y-1 group">
                      <div className="absolute top-0 -left-[100%] w-[120%] h-full block transform skew-x-[-20deg] bg-gradient-to-r from-transparent via-white/20 to-transparent group-hover:left-[200%] transition-all duration-700 ease-in-out pointer-events-none delay-75" />
                      <div className="relative z-10 flex items-center gap-[clamp(12px,3cqw,16px)] overflow-hidden">
                        <div className="w-[clamp(40px,8cqw,56px)] h-[clamp(40px,8cqw,56px)] shrink-0 rounded-[clamp(12px,2.5cqw,16px)] bg-gradient-to-br from-emerald-400 to-green-600 flex items-center justify-center text-white shadow-lg shadow-green-500/30">
                          <Leaf className="w-[clamp(24px,4cqw,28px)] h-[clamp(24px,4cqw,28px)]" fill="currentColor" />
                        </div>
                        <div className="flex flex-col items-start min-w-0 pr-2">
                          <span className="text-white text-[clamp(14px,3cqw,18px)] font-semibold tracking-wide truncate w-full text-left">调节干预</span>
                          <span className="text-white/60 text-[clamp(12px,2cqw,14px)] mt-0.5 truncate w-full text-left">自助调节</span>
                        </div>
                      </div>
                      <div className="relative z-10 w-[clamp(24px,4cqw,32px)] h-[clamp(24px,4cqw,32px)] shrink-0 rounded-full border border-white/30 flex items-center justify-center text-white/70 group-hover:text-white group-hover:border-white/60 transition-colors">
                        <svg className="w-[clamp(12px,2cqw,16px)] h-[clamp(12px,2cqw,16px)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </button>

                    <button 
                      onClick={handleStartConsultation}
                      className="relative overflow-hidden flex justify-between items-center bg-white/10 hover:bg-white/20 backdrop-blur-lg border border-white/40 rounded-[clamp(16px,4cqw,24px)] p-[clamp(16px,3cqw,20px)] transition-all duration-300 hover:-translate-y-1 group"
                    >
                      <div className="absolute top-0 -left-[100%] w-[120%] h-full block transform skew-x-[-20deg] bg-gradient-to-r from-transparent via-white/20 to-transparent group-hover:left-[200%] transition-all duration-700 ease-in-out pointer-events-none delay-100" />
                      <div className="relative z-10 flex items-center gap-[clamp(12px,3cqw,16px)] overflow-hidden">
                        <div className="w-[clamp(40px,8cqw,56px)] h-[clamp(40px,8cqw,56px)] shrink-0 rounded-[clamp(12px,2.5cqw,16px)] bg-gradient-to-br from-indigo-400 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/30">
                          <MessageSquare className="w-[clamp(24px,4cqw,28px)] h-[clamp(24px,4cqw,28px)]" fill="currentColor" />
                        </div>
                        <div className="flex flex-col items-start min-w-0 pr-2">
                          <span className="text-white text-[clamp(14px,3cqw,18px)] font-semibold tracking-wide truncate w-full text-left">问诊准备</span>
                          <span className="text-white/60 text-[clamp(12px,2cqw,14px)] mt-0.5 truncate w-full text-left">档案与设备确认</span>
                        </div>
                      </div>
                      <div className="relative z-10 w-[clamp(24px,4cqw,32px)] h-[clamp(24px,4cqw,32px)] shrink-0 rounded-full border border-white/30 flex items-center justify-center text-white/70 group-hover:text-white group-hover:border-white/60 transition-colors">
                        <svg className="w-[clamp(12px,2cqw,16px)] h-[clamp(12px,2cqw,16px)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </button>

                    <button className="relative overflow-hidden flex justify-between items-center bg-white/10 hover:bg-white/20 backdrop-blur-lg border border-white/40 rounded-[clamp(16px,4cqw,24px)] p-[clamp(16px,3cqw,20px)] transition-all duration-300 hover:-translate-y-1 group">
                      <div className="absolute top-0 -left-[100%] w-[120%] h-full block transform skew-x-[-20deg] bg-gradient-to-r from-transparent via-white/20 to-transparent group-hover:left-[200%] transition-all duration-700 ease-in-out pointer-events-none delay-150" />
                      <div className="relative z-10 flex items-center gap-[clamp(12px,3cqw,16px)] overflow-hidden">
                        <div className="w-[clamp(40px,8cqw,56px)] h-[clamp(40px,8cqw,56px)] shrink-0 rounded-[clamp(12px,2.5cqw,16px)] bg-gradient-to-br from-purple-400 to-pink-600 flex items-center justify-center text-white shadow-lg shadow-pink-500/30">
                          <User className="w-[clamp(24px,4cqw,28px)] h-[clamp(24px,4cqw,28px)]" fill="currentColor" />
                        </div>
                        <div className="flex flex-col items-start min-w-0 pr-2">
                          <span className="text-white text-[clamp(14px,3cqw,18px)] font-semibold tracking-wide truncate w-full text-left">个人档案</span>
                          <span className="text-white/60 text-[clamp(12px,2cqw,14px)] mt-0.5 truncate w-full text-left">管理与设置</span>
                        </div>
                      </div>
                      <div className="relative z-10 w-[clamp(24px,4cqw,32px)] h-[clamp(24px,4cqw,32px)] shrink-0 rounded-full border border-white/30 flex items-center justify-center text-white/70 group-hover:text-white group-hover:border-white/60 transition-colors">
                        <svg className="w-[clamp(12px,2cqw,16px)] h-[clamp(12px,2cqw,16px)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </button>
                  </div>

               </div>
            </div>
            
          </div>
        </div>
      </main>
    </div>
  );
}

