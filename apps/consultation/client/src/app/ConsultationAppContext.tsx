import { createContext, useContext, type ReactNode } from "react";
import type { ConsultationAppStore } from "./useConsultationApp";

const ConsultationAppContext = createContext<ConsultationAppStore | null>(null);

export function ConsultationAppProvider({
  value,
  children,
}: {
  value: ConsultationAppStore;
  children: ReactNode;
}) {
  return <ConsultationAppContext.Provider value={value}>{children}</ConsultationAppContext.Provider>;
}

export function useConsultationAppContext() {
  const value = useContext(ConsultationAppContext);

  if (!value) {
    throw new Error("useConsultationAppContext must be used within ConsultationAppProvider");
  }

  return value;
}
