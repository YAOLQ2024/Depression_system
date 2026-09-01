import { Shield } from "lucide-react";

export const entryBackgroundStyle = {
  backgroundImage:
    "linear-gradient(90deg, rgba(14,24,56,0.52) 0%, rgba(18,32,72,0.30) 34%, rgba(18,32,72,0.10) 60%, rgba(18,32,72,0.22) 100%), url('/yun.jpg')",
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
    <header className={cx("absolute left-[clamp(1rem,2.1vw,2.6rem)] top-[clamp(1rem,2.1vw,2.4rem)] z-20", className)}>
      <div className="rounded-[clamp(18px,2.4vw,30px)] border border-white/30 bg-white/30 px-[clamp(0.75rem,1.3vw,1.25rem)] py-[clamp(0.7rem,1.2vw,1.05rem)] shadow-[0_18px_44px_rgba(3,12,40,0.28)] backdrop-blur-xl">
        <img
          alt="Artificial Intelligence in Medicine Lab"
          className="h-auto w-[clamp(11rem,22vw,29rem)] max-w-[72vw] object-contain"
          src="/aim-brand-lockup-transparent-clean.png"
        />
      </div>
    </header>
  );
}

export function EntryFooter({ className }: EntryFooterProps) {
  return (
    <footer
      className={cx(
        "absolute inset-x-0 bottom-0 z-20 flex w-full justify-center px-[clamp(1rem,3vw,2.4rem)] pb-[clamp(1rem,2vw,1.7rem)]",
        className,
      )}
    >
      <div className="flex w-full max-w-[1120px] flex-col items-center justify-center gap-1.5 text-center text-[clamp(0.82rem,0.78vw,1.02rem)] leading-[1.7] text-[#7b54c6]/86">
        <div className="inline-flex items-center gap-2">
          <Shield className="h-[clamp(0.9rem,0.88vw,1.08rem)] w-[clamp(0.9rem,0.88vw,1.08rem)]" />
          <span>所有信息仅用于医疗评估流程，传输与存储均受保护。</span>
        </div>
        <p>本系统用于辅助评估，不替代临床诊断。</p>
      </div>
    </footer>
  );
}
