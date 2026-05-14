import type { ReactNode } from "react";

import { LogOut, Shield } from "lucide-react";

import { ActionButton, cx, StatusPill } from "../components/patient-ui";
import type { UserRecord } from "../types";
import { SIDEBAR_STEPS } from "../workflow";

type ConsultationShellProps = {
  title: string;
  breadcrumb: string;
  sidebarStep: number;
  user: UserRecord;
  message?: string;
  error?: string;
  onLogout: () => void | Promise<void>;
  children: ReactNode;
};

function ConsultationShell({
  title,
  breadcrumb,
  sidebarStep,
  user,
  message,
  error,
  onLogout,
  children,
}: ConsultationShellProps) {
  return (
    <div className="grid min-h-screen grid-cols-1 bg-[linear-gradient(180deg,#d8deff_0%,#9cb8ff_46%,#7f8dff_100%)] text-slate-900 xl:grid-cols-[310px_minmax(0,1fr)]">
      <aside className="relative border-b border-white/14 bg-[linear-gradient(180deg,rgba(93,87,214,0.44),rgba(72,93,192,0.26))] px-6 py-6 text-white backdrop-blur-xl xl:border-b-0 xl:border-r">
        <div className="space-y-8">
          <div className="rounded-[22px] bg-white/8 px-3.5 py-3.5 shadow-[0_18px_40px_rgba(10,18,40,0.14)] ring-1 ring-white/12 backdrop-blur-md">
            <img
              alt="Artificial Intelligence in Medicine Lab"
              className="h-14 w-auto object-contain"
              src="/aim-brand-lockup.svg"
            />
          </div>

          <nav className="grid gap-3">
            {SIDEBAR_STEPS.map((step, index) => {
              const isActive = sidebarStep === index;
              const isComplete = sidebarStep > index;

              return (
                <div
                  key={step.title}
                  className={cx(
                    "flex items-start gap-4 rounded-[24px] border px-4 py-4 transition",
                    isActive && "border-white/22 bg-white/16 shadow-[0_18px_40px_rgba(45,58,156,0.18)]",
                    !isActive && "border-white/8 bg-white/6",
                  )}
                >
                  <div
                    className={cx(
                      "flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-sm font-semibold",
                      isActive && "bg-white text-[#24459f]",
                      isComplete && !isActive && "bg-emerald-100 text-emerald-700",
                      !isActive && !isComplete && "bg-white/10 text-white/72",
                    )}
                  >
                    {index + 1}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-white">{step.title}</p>
                    <p className="mt-1 text-sm leading-6 text-white/64">{step.description}</p>
                  </div>
                </div>
              );
            })}
          </nav>
        </div>

        <div className="mt-6 xl:absolute xl:bottom-6 xl:left-6 xl:right-6">
          <div className="rounded-[24px] border border-white/12 bg-white/10 p-4 backdrop-blur-md">
            <p className="text-sm font-semibold text-white">流程说明</p>
            <p className="mt-2 text-sm leading-6 text-white/66">如需中断，系统会保留当前步骤，重新登录后可继续完成。</p>
          </div>
        </div>
      </aside>

      <main className="px-5 py-5 md:px-6 md:py-6 xl:px-7 xl:py-6">
        <header className="mb-5 flex flex-col gap-4 rounded-[30px] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(248,250,255,0.94),rgba(238,243,255,0.88))] px-5 py-5 shadow-[0_20px_60px_rgba(10,18,40,0.12)] backdrop-blur-xl lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-[2rem] font-semibold tracking-[-0.05em] text-slate-950">{title}</h1>
            <p className="mt-2 text-sm tracking-[0.02em] text-slate-500">{breadcrumb}</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <StatusPill tone="positive">
              <Shield size={13} />
              医疗级数据安全保护中
            </StatusPill>
            <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-white/80 px-3 py-2 shadow-[0_10px_24px_rgba(10,18,40,0.08)]">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#315CFF] text-sm font-semibold text-white">
                {user.full_name.slice(0, 1)}
              </div>
              <div className="pr-1">
                <p className="text-sm font-semibold text-slate-900">{user.full_name}</p>
                <p className="text-xs text-slate-500">{user.id}</p>
              </div>
            </div>
            <ActionButton className="gap-2" onClick={onLogout} variant="secondary">
              <LogOut size={15} />
              退出
            </ActionButton>
          </div>
        </header>

        {message ? (
          <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
            {message}
          </div>
        ) : null}
        {error ? (
          <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700" role="alert">
            {error}
          </div>
        ) : null}

        {children}
      </main>
    </div>
  );
}

export default ConsultationShell;
