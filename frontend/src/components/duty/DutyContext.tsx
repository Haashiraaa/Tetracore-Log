// frontend/src/components/duty/DutyContext.tsx
// Where the signed-in officer stands: on duty at a gate, or off duty. Only accounts that
// belong to a facility log duty; everyone else gets `null` from useDuty().
//
// Nothing at the gate can be logged off duty (the server refuses it), so the app keeps this
// fresh: loaded on start, after every duty action, and every few minutes in case an admin
// took the officer off duty.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { DutyStatus } from "@/api/schemas";
import { useInterval } from "@/hooks/useInterval";
import * as dutyService from "@/services/dutyService";

const DUTY_REFRESH_MS = 60_000;

interface DutyContextValue {
  /** null until the first answer arrives. */
  status: DutyStatus | null;
  onDuty: boolean;
  gate: number | null;
  /** The first load failed: the app cannot tell, so it lets the server decide. */
  unknown: boolean;
  set(next: DutyStatus): void;
  refresh(): void;
}

const DutyContext = createContext<DutyContextValue | null>(null);

export function DutyProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<DutyStatus | null>(null);
  const [unknown, setUnknown] = useState(false);

  const refresh = useCallback(() => {
    dutyService
      .status()
      .then((s) => {
        setStatus(s);
        setUnknown(false);
      })
      .catch(() => setUnknown(true));
  }, []);

  useEffect(refresh, [refresh]);
  useInterval(refresh, DUTY_REFRESH_MS);

  const value = useMemo<DutyContextValue>(
    () => ({
      status,
      onDuty: status?.current != null,
      gate: status?.current?.gate ?? null,
      unknown,
      set: (next) => {
        setStatus(next);
        setUnknown(false);
      },
      refresh,
    }),
    [status, unknown, refresh],
  );
  return <DutyContext.Provider value={value}>{children}</DutyContext.Provider>;
}

/** null for accounts that do not log duty (they have no DutyProvider above them). */
export function useDuty(): DutyContextValue | null {
  return useContext(DutyContext);
}
