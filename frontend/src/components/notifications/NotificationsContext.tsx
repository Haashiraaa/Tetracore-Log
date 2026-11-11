// frontend/src/components/notifications/NotificationsContext.tsx
// The bell's numbers, shared by the sidebar badge and the Notifications page. Only admins get
// one (AppShell wraps itself in it for them). It asks the server every few seconds; when the
// newest event id moves, the page fetches what is new.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import * as eventsApi from "@/api/events";
import type { EventsSummary } from "@/api/schemas";
import { NOTIFICATIONS_POLL_MS } from "@/config/env";
import { useInterval } from "@/hooks/useInterval";

interface NotificationsValue {
  /** null until the first answer. */
  summary: EventsSummary | null;
  refresh: () => Promise<void>;
  /** Everything so far counts as read. */
  markAllRead: () => Promise<void>;
}

const Ctx = createContext<NotificationsValue | null>(null);

/** null when this person is not an admin (no provider above). */
export function useNotifications(): NotificationsValue | null {
  return useContext(Ctx);
}

const BASE_TITLE = "Tetracore Log";

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [summary, setSummary] = useState<EventsSummary | null>(null);

  const refresh = useCallback(async () => {
    try {
      setSummary(await eventsApi.summary());
    } catch {
      // Offline or a hiccup: keep the last numbers, the next tick tries again.
    }
  }, []);

  const markAllRead = useCallback(async () => {
    setSummary(await eventsApi.markRead());
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);
  useInterval(() => void refresh(), NOTIFICATIONS_POLL_MS);

  // A tab left open in the background still shows that something needs a look.
  const unread = summary?.unread ?? 0;
  useEffect(() => {
    document.title = unread > 0 ? `(${unread > 99 ? "99+" : unread}) ${BASE_TITLE}` : BASE_TITLE;
    return () => {
      document.title = BASE_TITLE;
    };
  }, [unread]);

  const value = useMemo(() => ({ summary, refresh, markAllRead }), [summary, refresh, markAllRead]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
