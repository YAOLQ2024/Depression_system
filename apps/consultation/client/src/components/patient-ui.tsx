import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

type ClassValue = string | false | null | undefined;

export function cx(...values: ClassValue[]) {
  return values.filter(Boolean).join(" ");
}

export function SurfaceCard({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx(
        "rounded-[30px] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(248,250,255,0.96),rgba(238,243,255,0.92))] text-slate-900 shadow-[0_24px_80px_rgba(10,18,40,0.14)] backdrop-blur-xl",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function SideCard({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <SurfaceCard className={cx("p-5", className)} {...props}>
      {children}
    </SurfaceCard>
  );
}

type SectionHeadingProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
};

export function SectionHeading({ eyebrow, title, description, action }: SectionHeadingProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="space-y-3">
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">{eyebrow}</p>
        ) : null}
        <div className="space-y-2">
          <h2 className="text-[1.9rem] font-semibold tracking-[-0.05em] text-slate-950">{title}</h2>
          {description ? <p className="max-w-[44rem] text-sm leading-7 text-slate-600">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

type ActionButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
};

export function ActionButton({
  variant = "primary",
  className,
  type = "button",
  ...props
}: ActionButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-2xl text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" &&
          "bg-[#315CFF] px-5 py-3.5 text-white shadow-[0_18px_36px_rgba(49,92,255,0.24)] hover:-translate-y-0.5 hover:bg-[#2549d6]",
        variant === "secondary" &&
          "border border-slate-200 bg-slate-50 px-5 py-3.5 text-slate-700 backdrop-blur-md hover:border-slate-300 hover:bg-white",
        variant === "ghost" && "px-3 py-2 text-slate-500 hover:text-slate-800",
        className,
      )}
      {...props}
    />
  );
}

export function FormField({
  label,
  className,
  children,
}: {
  label: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <label className={cx("flex flex-col gap-2.5", className)}>
      <span className="text-sm font-semibold text-slate-800">{label}</span>
      {children}
    </label>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cx(
        "h-13 rounded-2xl border border-slate-200 bg-white px-4 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[#315CFF] focus:ring-4 focus:ring-blue-100",
        props.className,
      )}
    />
  );
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cx(
        "min-h-[132px] rounded-2xl border border-slate-200 bg-white px-4 py-3.5 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-[#315CFF] focus:ring-4 focus:ring-blue-100",
        props.className,
      )}
    />
  );
}

export function StatusPill({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "positive";
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium backdrop-blur-sm",
        tone === "neutral" && "border-slate-200 bg-slate-100 text-slate-600",
        tone === "positive" && "border-emerald-200 bg-emerald-50 text-emerald-700",
      )}
    >
      {children}
    </span>
  );
}

export function ProgressSteps({
  items,
  currentStep,
}: {
  items: string[];
  currentStep: number;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
      {items.map((item, index) => {
        const stepNumber = index + 1;
        const status =
          currentStep === stepNumber ? "current" : currentStep > stepNumber ? "done" : "upcoming";

        return (
          <div
            key={item}
            className={cx(
              "rounded-2xl border px-4 py-4 transition",
              status === "current" && "border-blue-200 bg-blue-50",
              status === "done" && "border-emerald-200 bg-emerald-50/80",
              status === "upcoming" && "border-slate-200 bg-white/88",
            )}
          >
            <div className="mb-3 flex items-center gap-3">
              <div
                className={cx(
                  "flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold",
                  status === "current" && "bg-[#315CFF] text-white",
                  status === "done" && "bg-emerald-100 text-emerald-700",
                  status === "upcoming" && "bg-slate-100 text-slate-500",
                )}
              >
                {stepNumber}
              </div>
              <div className="h-px flex-1 bg-slate-200" />
            </div>
            <p className="text-sm font-medium text-slate-700">{item}</p>
          </div>
        );
      })}
    </div>
  );
}
