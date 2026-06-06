import { cn } from "../../../lib/utils";

interface DigitalCounselorProps {
  imageSrc?: string;
  title?: string;
  className?: string;
}

export function DigitalCounselor({
  imageSrc = "/home-digital-human.png",
  title = "数字心理咨询师",
  className,
}: DigitalCounselorProps) {
  return (
    <div className={cn("flex h-full w-full items-end justify-center overflow-hidden", className)}>
      <img
        src={imageSrc}
        alt={title}
        className="relative z-10 block h-auto max-h-[calc(100vh-190px)] w-full max-w-[312px] origin-bottom scale-[1.15] translate-y-[10px] select-none object-contain object-bottom drop-shadow-[0_24px_48px_rgba(15,23,42,0.28)] xl:max-w-[328px] xl:max-h-[calc(100vh-180px)]"
        draggable={false}
      />
    </div>
  );
}
