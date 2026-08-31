import React, { useEffect, useState } from "react";
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

function FullScreenBackground({ imageSrc }: { imageSrc: string }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const image = new Image();
    image.src = imageSrc;
    if (image.complete) {
      setLoaded(true);
      return;
    }
    image.onload = () => setLoaded(true);
    return () => {
      image.onload = null;
    };
  }, [imageSrc]);

  return (
    <div className="absolute inset-0 z-0 overflow-hidden bg-[radial-gradient(circle_at_50%_0%,#40506a,#111827_72%)]">
      <img
        src={imageSrc}
        alt=""
        aria-hidden="true"
        onLoad={() => setLoaded(true)}
        className={`absolute inset-0 h-full w-full object-cover object-center transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
      />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(10,18,34,0.14),rgba(10,18,34,0.22))]" />
    </div>
  );
}

export function ConsultationLayout({ children, backgroundImage, title }: { children: React.ReactNode, backgroundImage?: string, title?: string | null | false }) {
  return (
    <div className="h-screen w-full flex flex-col font-sans overflow-hidden bg-slate-900 relative z-0">
      {backgroundImage ? (
        <FullScreenBackground imageSrc={backgroundImage} />
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
