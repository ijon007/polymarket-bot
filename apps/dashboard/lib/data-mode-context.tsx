"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "dashboard-data-mode";

export type DataMode = "paper" | "live";

function readStored(): DataMode {
  if (typeof window === "undefined") return "live";
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "paper" || v === "live") return v;
  } catch {
    /* ignore */
  }
  return "live";
}

type DataModeContextValue = {
  dataMode: DataMode;
  setDataMode: (mode: DataMode) => void;
};

const DataModeContext = createContext<DataModeContextValue | null>(null);

export function DataModeProvider({ children }: { children: ReactNode }) {
  const [dataMode, setDataModeState] = useState<DataMode>("live");
  useEffect(() => {
    setDataModeState(readStored());
  }, []);
  const setDataMode = useCallback((mode: DataMode) => {
    setDataModeState(mode);
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      /* ignore */
    }
  }, []);
  const value = useMemo(
    () => ({ dataMode, setDataMode }),
    [dataMode, setDataMode]
  );
  return (
    <DataModeContext.Provider value={value}>{children}</DataModeContext.Provider>
  );
}

export function useDataMode(): DataModeContextValue {
  const ctx = useContext(DataModeContext);
  if (!ctx) {
    return {
      dataMode: "live",
      setDataMode: () => {},
    };
  }
  return ctx;
}
