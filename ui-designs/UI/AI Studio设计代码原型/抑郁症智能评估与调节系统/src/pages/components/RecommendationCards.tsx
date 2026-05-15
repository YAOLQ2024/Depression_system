import { Play } from "lucide-react";
import { SoftCard } from "../../components/SoftCard";

const RECOMMENDATIONS = [
  { img: "https://images.unsplash.com/photo-1506126613408-eca07ce68773?q=80&w=600&auto=format&fit=crop", title: "呼吸放松训练", desc: "5-10分钟 · 缓解焦虑" },
  { img: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?q=80&w=600&auto=format&fit=crop", title: "舒缓音乐", desc: "20分钟 · 放松心情" },
  { img: "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?q=80&w=600&auto=format&fit=crop", title: "正念冥想引导", desc: "10分钟 · 提升专注" },
  { img: "https://images.unsplash.com/photo-1517842645767-c639042777db?q=80&w=600&auto=format&fit=crop", title: "心理小贴士", desc: "每日一条 · 温暖陪伴" }
];

export function RecommendationCards() {
  return (
    <div className="mb-4">
      <h3 className="text-lg font-semibold text-slate-800 mb-4 px-1">为你推荐</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {RECOMMENDATIONS.map((rec, i) => (
          <SoftCard key={i} className="relative h-20 overflow-hidden group flex items-end p-0">
            {/* Background Image with Gradient Overlay */}
            <img src={rec.img} alt={rec.title} className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />
            <div className="absolute inset-0 bg-gradient-to-r from-slate-900/70 via-slate-800/40 to-transparent"></div>
            
            <div className="relative z-10 p-4 w-full flex justify-between items-end pb-3">
              <div>
                <h4 className="font-medium text-white text-sm drop-shadow-sm mb-0.5">{rec.title}</h4>
                <p className="text-white/80 text-[10px] drop-shadow-sm">{rec.desc}</p>
              </div>
              <button className="w-6 h-6 rounded-full bg-white/30 backdrop-blur-md flex items-center justify-center text-white border border-white/40 hover:bg-white hover:text-primary-600 transition-colors">
                <Play className="w-3 h-3 ml-0.5 fill-current" />
              </button>
            </div>
          </SoftCard>
        ))}
      </div>
    </div>
  );
}
