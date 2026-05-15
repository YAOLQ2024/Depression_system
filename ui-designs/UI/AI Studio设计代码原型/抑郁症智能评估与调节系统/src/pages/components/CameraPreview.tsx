import { Sun } from "lucide-react";
import { cn } from "../../lib/utils";

interface CameraPreviewProps {
  className?: string; // For absolute positioning depending on state
}

export function CameraPreview({ className }: CameraPreviewProps) {
  return (
    <div className={cn("glass-card overflow-hidden w-64 h-44 flex flex-col z-50 shadow-lg border border-white/60", className)}>
      <div className="absolute top-3 left-3 flex items-center gap-1.5 z-10 bg-black/30 backdrop-blur-md px-2 py-1 rounded-full">
        <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></div>
        <span className="text-[10px] text-white font-medium tracking-wide">表情监测中</span>
      </div>
      
      {/* Simulation of camera feed */}
      <img 
        src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=400&auto=format&fit=crop" 
        alt="Camera feed" 
        className="w-full h-full object-cover"
        style={{ transform: "scaleX(-1)" }} // Mirror effect for camera
      />
      
      <div className="absolute bottom-2 inset-x-2 flex justify-between items-center z-10">
         <div className="flex items-center gap-1 bg-black/40 backdrop-blur-md px-2 py-1.5 rounded-lg">
           <Sun className="w-3 h-3 text-yellow-300" />
           <span className="text-[10px] text-white">光线良好</span>
         </div>
         {/* Fake volume bars */}
         <div className="flex items-end gap-0.5 bg-black/40 backdrop-blur-md p-1.5 rounded-lg h-6">
           <div className="w-1 bg-white/80 rounded z-10 h-2"></div>
           <div className="w-1 bg-white/80 rounded z-10 h-3"></div>
           <div className="w-1 bg-white/40 rounded z-10 h-4"></div>
           <div className="w-1 bg-white/40 rounded z-10 h-2"></div>
         </div>
      </div>
    </div>
  );
}
