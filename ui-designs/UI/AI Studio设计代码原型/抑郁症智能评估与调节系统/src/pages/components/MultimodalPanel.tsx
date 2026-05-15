import { type MultimodalData } from "../../types/consultation";
import { CameraPreview } from "./CameraPreview";
import { cn } from "../../lib/utils";
import { Smile } from "lucide-react";
import { ReactNode } from "react";

interface MultimodalPanelProps {
  data: MultimodalData | null;
  onClose: () => void;
}

export function MultimodalPanel({ data, onClose }: MultimodalPanelProps) {
  if (!data) return null;

  return (
    <div className="w-full min-h-full font-sans text-slate-100 flex flex-col pt-0 bg-slate-900/40">
        
        {/* Header */}
        <div className="flex items-center justify-between py-4 px-6 top-0 sticky bg-slate-900/80 backdrop-blur-md z-10 border-b border-indigo-500/20 shadow-md">
          <h2 className="text-[20px] font-semibold tracking-wide text-white">多模态实时监测</h2>
          <div className="flex items-center gap-2 text-xs text-green-400">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
            实时监测中
          </div>
        </div>

        <div className="flex-1 flex flex-col gap-5 p-5">
        {/* Grid Row 1 */}
        <div className="grid grid-cols-2 gap-5">
          <DarkCard title="摄像头画面" hasStatus>
            <div className="w-full aspect-video rounded-xl overflow-hidden relative">
              {/* Assuming CameraPreview can be used without the outer card if we pass a class that hides its frame. But we'll just embed it. */}
              <CameraPreview className="w-full h-full !rounded-none !border-none !shadow-none" />
            </div>
          </DarkCard>

          <DarkCard title="表情识别" hasStatus>
             <div className="flex flex-col h-full justify-center">
               <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center text-green-400">
                     <Smile className="w-8 h-8" />
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-green-400">平静</div>
                    <div className="text-sm text-slate-300 ml-1">76%</div>
                  </div>
               </div>
               
               <div className="space-y-2 mt-auto">
                 <ProgressBar label="中性" val="15%" pct={15} color="bg-blue-500" />
                 <ProgressBar label="轻度悲伤" val="7%" pct={7} color="bg-blue-500" />
                 <ProgressBar label="焦虑" val="2%" pct={2} color="bg-blue-500" />
                 <ProgressBar label="其他" val="0%" pct={0} color="bg-blue-500" />
               </div>
             </div>
          </DarkCard>
        </div>

        {/* Grid Row 2 */}
        <div className="grid grid-cols-2 gap-5">
          <DarkCard title="姿态状态" hasStatus>
            <div className="flex items-center justify-between h-full py-2">
               <div className="relative w-16 h-20">
                  {/* Mock pose icon */}
                  <img src="https://images.unsplash.com/photo-1544256718-3bcf237f3974?q=80&w=100&auto=format&fit=crop" alt="Pose" className="w-full h-full object-cover mix-blend-screen opacity-60 rounded" />
               </div>
               <div className="flex flex-col items-end gap-2">
                 <span className="text-slate-300 text-sm">坐姿端正</span>
                 <span className="text-green-400 font-medium">稳定 92%</span>
               </div>
            </div>
          </DarkCard>

          <DarkCard title="语音状态" hasStatus>
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <div className="flex items-center justify-center gap-1 w-full h-10 opacity-70">
                 {/* Fake waveform */}
                 {Array.from({length: 20}).map((_, i) => (
                   <div key={i} className="w-1 bg-blue-500 rounded-full" style={{ height: `${Math.random() * 100}%` }}></div>
                 ))}
              </div>
              <div className="text-green-400 font-medium self-end text-sm">语音平稳 88%</div>
            </div>
          </DarkCard>
        </div>

        {/* Grid Row 3: EEG */}
        <DarkCard title="脑电信号 (EEG)" hasStatus>
           <div className="flex items-center gap-4 h-32">
             {/* Channels */}
             <div className="flex-1 flex flex-col justify-between h-full text-[10px] text-slate-400">
               {['Fp1', 'Fp2', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2'].map(channel => (
                 <div key={channel} className="flex items-center gap-2">
                   <span className="w-6 shrink-0">{channel}</span>
                   <div className="flex-1 h-[2px] bg-blue-500/30 overflow-hidden relative">
                     <div className="absolute top-0 right-full w-full h-full bg-blue-400 animate-[pulse_2s_linear_infinite]" style={{ animationDelay: `${Math.random()}s` }}></div>
                   </div>
                 </div>
               ))}
             </div>
             {/* Brain map placeholder */}
             <div className="w-24 h-full relative flex items-center justify-center rounded-lg bg-blue-900/20 border border-blue-500/20">
               <span className="text-xs text-blue-300">脑电地形图</span>
             </div>
           </div>
        </DarkCard>

        {/* Grid Row 4: Text */}
        <DarkCard title="文本分析" hasStatus>
          <div className="flex justify-between items-center text-sm">
             <div className="space-y-2">
               <div className="text-slate-300">当前未检测到明显消极情绪词汇</div>
               <div className="text-slate-400">语言表达状态: <span className="text-green-400">正常</span></div>
             </div>
             <div className="flex flex-wrap gap-2 w-32 justify-end text-xs text-blue-300 opacity-60">
               <span>生活</span>
               <span>工作</span>
               <span>社交</span>
               <span>团队</span>
               <span>学习</span>
               <span>希望</span>
               <span>家人</span>
             </div>
          </div>
        </DarkCard>
        </div>
    </div>
  );
}

// Subcomponents

function DarkCard({ title, children, hasStatus }: { title: string, children: ReactNode, hasStatus?: boolean }) {
  return (
    <div className="bg-slate-800/40 rounded-2xl border border-white/10 p-5 flex flex-col relative overflow-hidden shadow-[0_4px_20px_rgba(0,0,0,0.2)]">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-medium text-slate-200">{title}</h3>
        {hasStatus && <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-green-500"></span><span className="text-[10px] text-slate-400">实时</span></div>}
      </div>
      <div className="flex-1">
        {children}
      </div>
    </div>
  );
}

function ProgressBar({ label, val, pct, color }: { label: string, val: string, pct: number, color: string }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-12 text-slate-400">{label}</span>
      <div className="flex-1 h-1 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }}></div>
      </div>
      <span className="w-8 text-right text-slate-400">{val}</span>
    </div>
  );
}
