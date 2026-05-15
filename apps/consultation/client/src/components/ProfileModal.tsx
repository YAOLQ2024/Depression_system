import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { LogOut, User } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useConsultationAppContext } from "../app/ConsultationAppContext";
import { cn } from "../lib/utils";
import { APP_PATHS } from "../routes";

type AnchorRect = {
  top: number;
  right: number;
  bottom: number;
  left: number;
  width: number;
  height: number;
};

type ShowProfileModalDetail = {
  anchorRect: AnchorRect;
  anchorEl: Element | null;
};

type MenuPosition = {
  top: number;
  left: number;
  transformOrigin: string;
};

export const SHOW_PROFILE_MODAL_EVENT = "SHOW_PROFILE_MODAL_EVENT";

function toAnchorRect(target: Element): AnchorRect {
  const rect = target.getBoundingClientRect();
  return {
    top: rect.top,
    right: rect.right,
    bottom: rect.bottom,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  };
}

function getFallbackAnchorRect(): AnchorRect {
  const width = 44;
  const height = 44;
  const right = window.innerWidth - 24;
  const top = 20;
  return {
    top,
    right,
    bottom: top + height,
    left: right - width,
    width,
    height,
  };
}

function getMenuPosition(anchor: AnchorRect, menuWidth: number, menuHeight = 0): MenuPosition {
  const viewportPadding = 16;
  const gap = 8;

  let left = anchor.right - menuWidth;
  left = Math.min(Math.max(left, viewportPadding), window.innerWidth - menuWidth - viewportPadding);

  let top = anchor.bottom + gap;
  let transformOrigin = "top right";

  if (menuHeight > 0 && top + menuHeight > window.innerHeight - viewportPadding) {
    top = Math.max(viewportPadding, anchor.top - menuHeight - gap);
    transformOrigin = "bottom right";
  }

  return { top, left, transformOrigin };
}

export function showProfileModal(anchor?: Element | null) {
  const detail: ShowProfileModalDetail = {
    anchorRect: anchor ? toAnchorRect(anchor) : getFallbackAnchorRect(),
    anchorEl: anchor || null,
  };
  window.dispatchEvent(new CustomEvent<ShowProfileModalDetail>(SHOW_PROFILE_MODAL_EVENT, { detail }));
}

export function ProfileModal() {
  const { state, actions } = useConsultationAppContext();
  const navigate = useNavigate();
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [anchorRect, setAnchorRect] = useState<AnchorRect | null>(null);
  const [anchorEl, setAnchorEl] = useState<Element | null>(null);
  const [position, setPosition] = useState<MenuPosition>({
    top: 20,
    left: 20,
    transformOrigin: "top right",
  });

  useEffect(() => {
    const handleShow = (event: Event) => {
      const detail = event instanceof CustomEvent ? (event.detail as ShowProfileModalDetail | undefined) : undefined;
      const nextAnchorEl = detail?.anchorEl || null;
      const nextAnchorRect = detail?.anchorRect || getFallbackAnchorRect();

      if (isOpen && anchorEl && nextAnchorEl && anchorEl === nextAnchorEl) {
        setIsOpen(false);
        return;
      }

      setAnchorEl(nextAnchorEl);
      setAnchorRect(nextAnchorRect);
      setPosition(getMenuPosition(nextAnchorRect, 180));
      setIsOpen(true);
    };

    window.addEventListener(SHOW_PROFILE_MODAL_EVENT, handleShow);
    return () => window.removeEventListener(SHOW_PROFILE_MODAL_EVENT, handleShow);
  }, [anchorEl, isOpen]);

  useEffect(() => {
    if (!state.user) {
      setIsOpen(false);
    }
  }, [state.user]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        setIsOpen(false);
        return;
      }

      if (menuRef.current?.contains(target)) {
        return;
      }

      if (anchorEl instanceof Node && anchorEl.contains(target)) {
        return;
      }

      setIsOpen(false);
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    window.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [anchorEl, isOpen]);

  useLayoutEffect(() => {
    if (!isOpen || !menuRef.current) {
      return;
    }

    const menuRect = menuRef.current.getBoundingClientRect();
    const anchor = anchorRect || getFallbackAnchorRect();
    setPosition(getMenuPosition(anchor, menuRect.width, menuRect.height));
  }, [anchorRect, isOpen]);

  const closeMenu = () => setIsOpen(false);

  const handleGoToPreparation = () => {
    closeMenu();
    navigate(APP_PATHS.preparation);
  };

  const handleContinueFlow = () => {
    closeMenu();
    navigate(state.homeEntryPath);
  };

  const handleLogout = async () => {
    await actions.handleLogout();
    closeMenu();
    navigate(APP_PATHS.login);
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[100] pointer-events-none">
      <div
        ref={menuRef}
        className="absolute z-[110] min-w-[180px] overflow-hidden rounded-xl border border-slate-700 bg-slate-800 py-1 shadow-2xl pointer-events-auto animate-in fade-in zoom-in-95 duration-150"
        style={{ top: `${position.top}px`, left: `${position.left}px`, transformOrigin: position.transformOrigin }}
      >
        <MenuItem
          iconClassName="text-slate-300"
          label="个人资料"
          onClick={handleGoToPreparation}
          icon={<User className="w-4 h-4" />}
        />
        <MenuItem
          iconClassName="text-slate-300"
          label={`当前流程：${state.homeEntryLabel}`}
          onClick={handleContinueFlow}
          icon={<span className="text-[10px] font-semibold">GO</span>}
        />
        <div className="mx-4 my-1 h-px bg-slate-700" />
        <MenuItem
          iconClassName="text-rose-400"
          label="退出登录"
          labelClassName="text-rose-400"
          onClick={handleLogout}
          icon={<LogOut className="w-4 h-4" />}
        />
      </div>
    </div>
  );
}

function MenuItem({
  icon,
  iconClassName,
  label,
  labelClassName,
  onClick,
}: {
  icon: ReactNode;
  iconClassName: string;
  label: string;
  labelClassName?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-xs font-medium text-slate-200 transition-colors hover:bg-white/5"
    >
      <div className={cn("flex h-4 w-4 items-center justify-center shrink-0", iconClassName)}>{icon}</div>
      <span className={cn("truncate", labelClassName)}>{label}</span>
    </button>
  );
}
