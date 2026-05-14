import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { EntryBrand, EntryFooter, entryBackgroundStyle } from "../components/entry-chrome";
import { APP_PATHS } from "../routes";

function CoverPage() {
  return (
    <main className="relative h-[100svh] overflow-hidden bg-[#0d1631]" style={entryBackgroundStyle}>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_34%_38%,rgba(255,255,255,0.16),transparent_22%),linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.02)_18%,rgba(255,255,255,0.08)_100%)]" />
      <div className="absolute inset-[20px] border border-white/12" />

      <EntryBrand />

      <section className="relative z-10 flex h-full items-center px-8 pb-22 pt-20 md:px-10 md:pb-26 md:pt-24">
        <div className="w-full max-w-[1320px]">
          <div className="max-w-[840px] lg:ml-12 xl:ml-20">
            <h1 className="max-w-none text-[clamp(2.8rem,5.6vw,5.6rem)] font-semibold leading-[0.94] tracking-[-0.07em] text-[#F4F7FF] [text-wrap:balance] [text-shadow:0_2px_22px_rgba(8,18,40,0.14)] md:whitespace-nowrap">
              抑郁症智能诊断与调节系统
            </h1>

            <p className="mt-6 max-w-[38rem] text-base font-medium leading-8 text-white/88 [text-shadow:0_1px_12px_rgba(8,18,40,0.16)] md:text-[1.08rem]">
              面向患者的数字问诊入口。登录后系统会自动恢复当前进度，并继续完成问诊准备、数字人问诊与量表评估。
            </p>

            <div className="mt-10 flex flex-wrap items-center gap-5">
              <Link
                className="inline-flex h-[3.35rem] items-center gap-3 rounded-full bg-[linear-gradient(180deg,#2452DA,#1E45BE)] px-7 text-[0.98rem] font-semibold tracking-[0.02em] text-white shadow-[0_16px_34px_rgba(9,18,44,0.24)] transition hover:-translate-y-0.5 hover:bg-[#1e45be]"
                to={APP_PATHS.login}
              >
                进入系统
                <ArrowRight size={17} />
              </Link>
            </div>

            <p className="mt-8 max-w-[34rem] text-sm leading-7 text-white/62 md:text-[0.94rem]">
              预计 10-15 分钟完成主要流程，支持中断后继续。
            </p>
          </div>
        </div>
      </section>

      <EntryFooter />
    </main>
  );
}

export default CoverPage;
