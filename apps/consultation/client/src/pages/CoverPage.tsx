import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { EntryBrand, EntryFooter, entryBackgroundStyle } from "../components/entry-chrome";
import { APP_PATHS } from "../routes";

function CoverPage() {
  return (
    <main className="cover-page relative h-[100svh] overflow-hidden bg-[#0d1631]" style={entryBackgroundStyle}>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_26%_34%,rgba(255,255,255,0.34),transparent_22%),radial-gradient(circle_at_70%_18%,rgba(236,214,255,0.2),transparent_18%),linear-gradient(125deg,rgba(255,255,255,0.09)_0%,rgba(255,255,255,0.03)_20%,rgba(255,255,255,0.14)_100%)]" />

      <EntryBrand className="cover-brand" />

      <section className="cover-content relative z-10 flex h-full items-center px-[clamp(1.4rem,4vw,4rem)] pb-[clamp(6.8rem,10vh,10rem)] pt-[clamp(6rem,9vh,8.5rem)]">
        <div className="w-full max-w-[1480px]">
          <div className="cover-hero relative max-w-[64rem] lg:ml-[clamp(1.5rem,4vw,5rem)]">
            <div className="absolute -inset-x-[clamp(1rem,3vw,3rem)] -inset-y-10 -z-10 rounded-[3rem] bg-[radial-gradient(circle_at_18%_32%,rgba(255,255,255,0.62),rgba(255,255,255,0.16)_48%,transparent_76%)] blur-2xl" />

            <h1 className="cover-title max-w-none text-[clamp(3.25rem,6vw,7.1rem)] font-semibold leading-[0.92] tracking-[-0.075em] text-[#6f42cf] [text-wrap:balance] [text-shadow:0_0_26px_rgba(255,255,255,0.32),0_16px_34px_rgba(91,58,189,0.18)] md:whitespace-nowrap">
              <span>情绪识别智能评测</span><span>与调节系统</span>
            </h1>

            <div className="cover-actions mt-[clamp(1.8rem,3vw,2.8rem)] flex flex-wrap items-center gap-5">
              <Link
                className="cover-enter group relative inline-flex overflow-hidden rounded-full p-[1.5px] shadow-[0_12px_0_rgba(73,56,176,0.48),0_30px_64px_rgba(68,51,182,0.34)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_16px_0_rgba(73,56,176,0.44),0_36px_78px_rgba(68,51,182,0.4)] active:translate-y-[4px] active:shadow-[0_8px_0_rgba(73,56,176,0.48),0_18px_40px_rgba(68,51,182,0.3)]"
                to={APP_PATHS.login}
              >
                <span className="absolute inset-0 rounded-full bg-[linear-gradient(135deg,#afbeff_0%,#7b7eff_18%,#5d57f4_54%,#3f36c5_100%)]" />
                <span className="absolute inset-[2px] rounded-full bg-[linear-gradient(180deg,rgba(255,255,255,0.32),rgba(255,255,255,0.04)_36%,rgba(35,23,126,0.3)_100%)]" />
                <span className="pointer-events-none absolute inset-x-[18%] top-[10%] h-[34%] rounded-full bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(255,255,255,0.08))] opacity-80 blur-sm" />
                <span className="cover-enter-label relative inline-flex items-center gap-[clamp(0.7rem,1vw,0.95rem)] rounded-full px-[clamp(1.7rem,2.7vw,2.5rem)] py-[clamp(0.95rem,1.45vw,1.18rem)] text-[clamp(1.02rem,1.28vw,1.2rem)] font-semibold tracking-[0.08em] text-[#f2e4ff]">
                  进入系统
                  <ArrowRight className="transition duration-300 group-hover:translate-x-1" size={18} />
                </span>
              </Link>
            </div>

            <p className="cover-slogan mt-[clamp(1.5rem,2.3vw,2.2rem)] max-w-[28rem] text-[clamp(1.18rem,1.95vw,1.76rem)] font-semibold leading-[1.55] tracking-[0.18em] text-[#8556d7] [text-shadow:0_0_16px_rgba(255,255,255,0.24)]">
              智护心境，温暖同行
            </p>
          </div>
        </div>
      </section>

      <EntryFooter className="cover-footer" />
    </main>
  );
}

export default CoverPage;
