import { Shield } from "lucide-react";

export const entryBackgroundStyle = {
  backgroundImage:
    "linear-gradient(90deg, rgba(14,24,56,0.52) 0%, rgba(18,32,72,0.30) 34%, rgba(18,32,72,0.10) 60%, rgba(18,32,72,0.22) 100%), url('/cover-background-v2.png')",
  backgroundPosition: "center",
  backgroundSize: "cover",
};

type EntryBrandProps = {
  className?: string;
};

type EntryFooterProps = {
  className?: string;
};

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function EntryBrand({ className }: EntryBrandProps) {
  return (
    <header className={cx("absolute left-8 top-8 z-20 md:left-10 md:top-10", className)}>
      <div className="rounded-[22px] bg-white/8 px-3.5 py-3.5 shadow-[0_14px_36px_rgba(18,32,72,0.16)] ring-1 ring-white/12 backdrop-blur-md">
        <img
          alt="Artificial Intelligence in Medicine Lab"
          className="h-10 w-auto object-contain md:h-12"
          src="/aim-brand-lockup-transparent-clean.png"
        />
      </div>
    </header>
  );
}

export function EntryFooter({ className }: EntryFooterProps) {
  return (
    <footer className={cx("absolute inset-x-0 bottom-0 z-20 flex w-full justify-center px-6 pb-5", className)}>
      <div className="flex w-full max-w-[980px] flex-col items-center justify-center gap-1 text-center text-[0.72rem] leading-5 text-white/40">
        <div className="inline-flex items-center gap-2">
          <Shield size={13} />
          <span>所有信息仅用于医疗评估流程，传输与存储均受保护。</span>
        </div>
        <p>本系统用于辅助评估，不替代临床诊断。</p>
      </div>
    </footer>
  );
}
