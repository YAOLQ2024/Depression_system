import React from "react";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { GlobalBackground } from "../components/GlobalBackground";

export function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen w-full flex flex-col font-sans overflow-hidden bg-transparent relative z-0">
      <GlobalBackground />
      <div className="relative z-10 w-full flex flex-col h-full">
        <Header />
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <main className="flex-1 h-full overflow-y-auto p-3 sm:p-4 scroll-smooth pb-20">
             <div className="w-full h-full min-h-max mx-auto max-w-7xl">
              {children}
             </div>
          </main>
        </div>
      </div>
    </div>
  );
}

export function ConsultationLayout({ children, backgroundImage, title }: { children: React.ReactNode, backgroundImage?: string, title?: string | null | false }) {
  return (
    <div className="h-screen w-full flex flex-col font-sans overflow-hidden bg-slate-900 relative z-0">
      {backgroundImage ? (
        <div 
          className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat transition-opacity duration-1000"
          style={{ backgroundImage: `url('${backgroundImage}')` }}
        >
          {/* Overlay to ensure readability and mood */}
          <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]"></div>
        </div>
      ) : (
        <GlobalBackground />
      )}
      <div className="relative z-10 w-full flex flex-col h-full">
        <Header theme="dark" title={title} />
        <main className="flex-1 relative flex z-20 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
