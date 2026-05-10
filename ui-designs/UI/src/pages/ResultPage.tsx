import React from 'react';
import { 
  BarChart, Activity, ShieldCheck, Heart, ArrowRight,
  TrendingUp, AlertTriangle, FileText, Download, Share2, PhoneCall,
  ChevronRight
} from 'lucide-react';
import { motion } from 'motion/react';
import { ResponsiveContainer, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';

interface ResultPageProps {
  onRestart: () => void;
}

const ResultPage: React.FC<ResultPageProps> = ({ onRestart }) => {
  const radarData = [
    { subject: '情绪状态', A: 120, fullMark: 150 },
    { subject: '焦虑水平', A: 98, fullMark: 150 },
    { subject: '压力韧性', A: 86, fullMark: 150 },
    { subject: '社交功能', A: 70, fullMark: 150 },
    { subject: '认知调节', A: 110, fullMark: 150 },
    { subject: '生理机能', A: 130, fullMark: 150 },
  ];

  return (
    <div className="max-w-[1200px] mx-auto space-y-6">
      {/* Top Summary Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Profile Card */}
        <div className="lg:col-span-2 bg-white rounded-[40px] p-8 border border-[#E6EEFB] shadow-sm relative overflow-hidden">
           <Heart className="absolute -right-10 -bottom-10 text-rose-50 w-64 h-64 opacity-50" />
           <div className="relative z-10">
             <div className="flex justify-between items-start mb-8">
               <div>
                 <span className="px-3 py-1 bg-rose-50 text-rose-600 text-[10px] font-bold rounded-full mb-3 inline-block">评估结论 · 实时生成</span>
                 <h2 className="text-3xl font-extrabold text-[#172033]">综合风险评估结果</h2>
               </div>
               <div className="px-4 py-2 bg-blue-50 border border-blue-100 rounded-2xl flex items-center gap-2">
                 <ShieldCheck size={16} className="text-blue-600" />
                 <span className="text-blue-600 text-xs font-bold font-mono">CODE: MCSR-8821</span>
               </div>
             </div>

             <div className="flex items-center gap-12">
               <div className="w-48 h-48 relative flex items-center justify-center">
                  <svg className="w-full h-full -rotate-90">
                    <circle cx="96" cy="96" r="88" className="fill-none stroke-gray-50 stroke-[12]" />
                    <motion.circle 
                     cx="96" cy="96" r="88" 
                     className="fill-none stroke-orange-400 stroke-[12] stroke-round"
                     strokeDasharray={2 * Math.PI * 88}
                     initial={{ strokeDashoffset: 2 * Math.PI * 88 }}
                     animate={{ strokeDashoffset: 2 * Math.PI * 88 * (1 - 0.65) }}
                     transition={{ duration: 1.5, delay: 0.5 }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                     <span className="text-4xl font-extrabold text-[#172033]">中度</span>
                     <span className="text-xs text-[#6B7893] font-bold uppercase tracking-widest mt-1">风险等级</span>
                  </div>
               </div>

               <div className="flex-1 space-y-6">
                 <div>
                   <p className="text-sm font-bold text-[#6B7893] mb-3">多模态特征分析表明：</p>
                   <div className="flex flex-wrap gap-2">
                     {['情绪波动较大', '轻微认知窄化', '睡眠质量偏低', '语音单调性上升'].map(t => (
                       <span key={t} className="px-3 py-1.5 bg-[#F5F8FF] border border-[#E6EEFB] rounded-xl text-xs font-semibold text-[#172033]">{t}</span>
                     ))}
                   </div>
                 </div>
                 <div className="p-4 bg-orange-50/50 border border-orange-100 rounded-2xl">
                   <div className="flex items-center gap-2 text-orange-600 mb-1">
                     <AlertTriangle size={16} />
                     <span className="text-xs font-bold italic">评估员笔记 (AI Assistant)</span>
                   </div>
                   <p className="text-xs text-orange-800 leading-relaxed font-medium">
                     建议您在未来一周内关注情绪负面循环。量表得分与语音情感特征存在高度一致性。建议必要时进行人工复核。
                   </p>
                 </div>
               </div>
             </div>
           </div>
        </div>

        {/* Stats Radar Card */}
        <div className="bg-[#172033] rounded-[40px] p-8 border border-white/10 shadow-2xl relative overflow-hidden flex flex-col items-center justify-center">
           <Activity className="absolute -top-10 -left-10 text-blue-500/10 w-48 h-48" />
           <div className="relative z-10 w-full h-full flex flex-col">
              <h3 className="text-white text-lg font-bold mb-6 flex justify-between items-center">
                多维数据分布
                <BarChart size={18} className="text-blue-400" />
              </h3>
              <div className="flex-1 w-full min-h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                    <PolarGrid stroke="#ffffff20" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#ffffff60', fontSize: 10 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                    <Radar
                      name="User"
                      dataKey="A"
                      stroke="#0F6BFF"
                      fill="#0F6BFF"
                      fillOpacity={0.6}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 flex justify-between gap-4">
                 <div className="bg-white/5 rounded-2xl p-3 flex-1 flex flex-col items-center">
                    <span className="text-[9px] text-white/40 uppercase font-bold">综合置信度</span>
                    <span className="text-sm font-bold text-emerald-400">89.4%</span>
                 </div>
                 <div className="bg-white/5 rounded-2xl p-3 flex-1 flex flex-col items-center">
                    <span className="text-[9px] text-white/40 uppercase font-bold">生理唤醒度</span>
                    <span className="text-sm font-bold text-blue-400">中等</span>
                 </div>
              </div>
           </div>
        </div>
      </div>

      {/* Main Analysis Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
         {/* Detailed Scores */}
         <div className="lg:col-span-3 space-y-6">
            <div className="bg-white rounded-[40px] p-8 border border-[#E6EEFB] shadow-sm">
               <h3 className="text-xl font-bold text-[#172033] mb-8 flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-50 rounded-2xl flex items-center justify-center">
                    <FileText className="text-[#0F6BFF]" size={20} />
                  </div>
                  量表详情评估
               </h3>
               
               <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {[
                    { label: 'PHQ-9 抑郁筛查', score: 14, status: '中度抑郁倾向', icon: TrendingUp, color: 'emerald' },
                    { label: 'SDS 抑郁自评', score: 58, status: '由于焦虑伴随', icon: Activity, color: 'blue' },
                  ].map((item, i) => (
                    <div key={i} className="p-6 bg-[#F5F8FF]/50 border border-[#E6EEFB] rounded-[32px] hover:shadow-lg transition-all group">
                       <div className="flex justify-between items-start mb-4">
                          <div>
                             <h4 className="font-bold text-[#172033] mb-1">{item.label}</h4>
                             <p className="text-[10px] text-[#6B7893] uppercase font-bold tracking-widest">Assessment Detail</p>
                          </div>
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center bg-white group-hover:bg-blue-600 group-hover:text-white transition-all`}>
                            <item.icon size={20} />
                          </div>
                       </div>
                       <div className="flex items-end justify-between">
                          <div className="text-5xl font-extrabold text-[#172033]">
                             {item.score} <span className="text-sm text-[#6B7893] font-bold">分</span>
                          </div>
                          <span className="px-3 py-1 bg-white border border-[#E6EEFB] rounded-full text-[10px] font-bold text-blue-600 shadow-sm">{item.status}</span>
                       </div>
                       <div className="mt-6 space-y-2">
                          <div className="flex justify-between text-[10px] font-bold text-[#6B7893] px-1 uppercase tracking-tighter">
                             <span>Risk Level</span>
                             <span>Moderate</span>
                          </div>
                          <div className="h-1.5 w-full bg-white rounded-full overflow-hidden border border-gray-100">
                             <div className="h-full bg-blue-600 rounded-full w-[65%]" />
                          </div>
                       </div>
                    </div>
                  ))}
               </div>
            </div>

            <div className="bg-white rounded-[40px] p-8 border border-[#E6EEFB] shadow-sm">
               <h3 className="text-xl font-bold text-[#172033] mb-8 flex items-center gap-3">
                  <div className="w-10 h-10 bg-emerald-50 rounded-2xl flex items-center justify-center">
                    <Activity className="text-emerald-500" size={20} />
                  </div>
                  干预性建议与行动计划
               </h3>
               
               <div className="space-y-4">
                  {[
                    { title: '情绪日记练习', desc: '建议每日记录三件正向反馈小事，缓解认知窄化倾向。', action: '前往练习', type: 'training' },
                    { title: '呼吸冥想引导', desc: '系统监测到您生理唤醒度略高，建议进行 5 分钟腹式呼吸训练。', action: '立即开始', type: 'meditation' },
                    { title: '专家预约咨询', desc: '针对您的中度风险评估，建议与资深心理咨询师进行深层次沟通。', action: '立即预约', type: 'consult' }
                  ].map((task, i) => (
                    <div key={i} className="flex items-center justify-between p-5 bg-white border border-[#E6EEFB] rounded-3xl hover:border-emerald-500/30 transition-all hover:translate-x-2">
                       <div className="flex items-center gap-4">
                          <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-white shadow-lg ${i === 2 ? 'bg-orange-500 shadow-orange-500/20' : 'bg-emerald-500 shadow-emerald-500/20'}`}>
                             {i === 0 && <FileText size={20} />}
                             {i === 1 && <Activity size={20} />}
                             {i === 2 && <PhoneCall size={20} />}
                          </div>
                          <div>
                             <h4 className="font-bold text-[#172033] text-sm">{task.title}</h4>
                             <p className="text-[10px] text-[#6B7893] leading-relaxed max-w-sm">{task.desc}</p>
                          </div>
                       </div>
                       <button className="h-10 px-4 bg-[#F5F8FF] border border-blue-50 text-blue-600 text-[10px] font-extrabold rounded-xl hover:bg-blue-600 hover:text-white transition-all uppercase tracking-wide">
                          {task.action}
                       </button>
                    </div>
                  ))}
               </div>
            </div>
         </div>

         {/* Sidebar Actions */}
         <div className="space-y-6">
            <div className="bg-[#0F6BFF] p-8 rounded-[40px] text-white shadow-xl shadow-blue-500/20 relative overflow-hidden group border border-blue-400">
               <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-110" />
               <h3 className="text-lg font-bold mb-6 relative z-10">正式诊断建议</h3>
               <p className="text-blue-100 text-xs leading-relaxed mb-6 relative z-10 font-medium">
                  本评估结果仅供辅助参考，不构成法定医疗诊断。建议扫描下方二维码，由专业医师进行面诊确认。
               </p>
               <div className="bg-white p-4 rounded-3xl mb-6 relative z-10 flex justify-center">
                  <div className="w-32 h-32 bg-gray-50 rounded-xl relative border-4 border-white shadow-inner flex items-center justify-center">
                     <div className="grid grid-cols-2 gap-2 opacity-20">
                        {Array.from({ length: 16 }).map((_, i) => (
                           <div key={i} className="w-2 h-2 bg-[#0F6BFF] rounded-sm" />
                        ))}
                     </div>
                     <span className="absolute text-[8px] font-bold text-[#6B7893] uppercase tracking-widest bg-white p-1">QR CODE Mock</span>
                  </div>
               </div>
               <button className="w-full h-14 bg-white text-[#0F6BFF] font-bold rounded-2xl flex items-center justify-center gap-2 hover:bg-blue-50 transition-all shadow-lg active:scale-95">
                  <Download size={20} />
                  下载完整报告
               </button>
            </div>

            <div className="bg-white rounded-3xl border border-[#E6EEFB] p-6 space-y-4">
               <button className="w-full h-12 flex items-center justify-between px-4 hover:bg-gray-50 rounded-xl transition-all border border-transparent hover:border-gray-100">
                  <div className="flex items-center gap-3">
                     <Share2 size={16} className="text-[#6B7893]" />
                     <span className="text-xs font-bold text-[#172033]">分享评估结果</span>
                  </div>
                  <ChevronRight size={14} className="text-[#6B7893]" />
               </button>
               <div className="h-[1px] bg-[#F5F8FF]" />
               <button 
                onClick={onRestart}
                className="w-full h-12 flex items-center justify-between px-4 hover:bg-gray-50 rounded-xl transition-all border border-transparent hover:border-gray-100"
               >
                  <div className="flex items-center gap-3">
                     <Heart size={16} className="text-rose-500" />
                     <span className="text-xs font-bold text-[#172033]">我要再次评估</span>
                  </div>
                  <ChevronRight size={14} className="text-[#6B7893]" />
               </button>
            </div>

            <div className="bg-emerald-50 border border-emerald-100 rounded-3xl p-6 flex flex-col items-center gap-3">
               <div className="w-12 h-12 bg-white rounded-2xl shadow-sm flex items-center justify-center text-emerald-500 border border-emerald-50">
                  <ShieldCheck size={24} />
               </div>
               <p className="text-[10px] text-emerald-800 text-center font-bold tracking-tight leading-relaxed">
                  您的所有数据均已加密备份至私有云，<br />
                  下次问诊将自动同步历史趋势。
               </p>
            </div>
         </div>
      </div>
    </div>
  );
};

export default ResultPage;
