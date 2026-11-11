// frontend/src/pages/notifications/NotificationsPage.tsx
// Everything that happens, newest first: gate sign-ins and sign-outs, admin changes, and the
// two warnings. New events slide in at the top by themselves (the bell polls; this page asks for
// what is newer than its top row when the newest id moves).
import { useCallback, useEffect, useRef, useState } from "react";
import * as eventsApi from "@/api/events";
import type { EventGroup, EventItem, Facility } from "@/api/schemas";
import { PushSwitch } from "@/components/notifications/PushSwitch";
import { useNotifications } from "@/components/notifications/NotificationsContext";
import { Badge } from "@/components/ui/Badge";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { SelectField } from "@/components/ui/TextField";
import { PAGE_SIZE } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { cx } from "@/lib/cx";
import { formatDateTime } from "@/lib/dates";
import * as adminApi from "@/api/admin";
import { GROUPS, eventLabel } from "@/services/notificationService";

type GroupChoice = EventGroup | "all";

export default function NotificationsPage() {
  const notifications = useNotifications();
  const summary = notifications?.summary ?? null;

  const [group, setGroup] = useState<GroupChoice>("all");
  const [facility, setFacility] = useState("");
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [facilities, setFacilities] = useState<Facility[]>([]);

  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const top = useRef(0); // newest id on screen, for "anything newer?"

  const filters = useCallback(
    () => ({ group: group === "all" ? undefined : group, facility_code: facility || undefined }),
    [group, facility],
  );

  useEffect(() => {
    adminApi.listFacilities().then(setFacilities).catch(() => undefined);
  }, []);

  // First page again whenever a filter changes.
  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    eventsApi
      .listEvents({ ...filters(), limit: PAGE_SIZE }, ctrl.signal)
      .then((rows) => {
        setEvents(rows);
        setHasMore(rows.length === PAGE_SIZE);
        top.current = rows[0]?.id ?? 0;
      })
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted) setError(errorMessage(e));
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false);
      });
    return () => ctrl.abort();
  }, [filters]);

  // Live: the newest id on the server moved past our top row, so fetch what is newer.
  const latest = summary?.latest_id ?? 0;
  useEffect(() => {
    if (loading || latest <= top.current) return;
    const ctrl = new AbortController();
    eventsApi
      .listEvents({ ...filters(), after_id: top.current, limit: 200 }, ctrl.signal)
      .then((fresh) => {
        if (ctrl.signal.aborted) return;
        // `latest` moves for events our filter hides too: remember we have looked that far.
        top.current = Math.max(top.current, latest);
        if (fresh.length === 0) return;
        setEvents((old) => {
          const seen = new Set(old.map((e) => e.id));
          return [...fresh.filter((e) => !seen.has(e.id)), ...old];
        });
      })
      .catch(() => undefined); // the next tick tries again
    return () => ctrl.abort();
  }, [latest, loading, filters]);

  async function loadMore() {
    const last = events[events.length - 1];
    if (!last) return;
    setLoadingMore(true);
    try {
      const older = await eventsApi.listEvents({ ...filters(), before_id: last.id, limit: PAGE_SIZE });
      setEvents((old) => [...old, ...older]);
      setHasMore(older.length === PAGE_SIZE);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoadingMore(false);
    }
  }

  const lastRead = summary?.last_read_id ?? Number.MAX_SAFE_INTEGER; // unknown yet: nothing is "new"
  const shown = unreadOnly ? events.filter((e) => e.id > lastRead) : events;
  const unread = summary?.unread ?? 0;

  return (
    <div className="page stack stack--lg">
      <PageHeader
        title="Notifications"
        subtitle={unread > 0 ? `${unread} new` : "Everything is read"}
        actions={
          <Button variant="secondary" disabled={unread === 0} onClick={() => void notifications?.markAllRead()}>
            Mark all as read
          </Button>
        }
      />

      <PushSwitch />

      <div className="filters">
        <div className="kind-tabs kind-tabs--four" role="tablist" aria-label="Which events">
          {GROUPS.map((g) => (
            <button
              key={g.value}
              type="button"
              role="tab"
              aria-selected={group === g.value}
              className="kind-tabs__tab"
              onClick={() => setGroup(g.value)}
            >
              {g.label}
            </button>
          ))}
        </div>
        <SelectField label="Facility" value={facility} onChange={(e) => setFacility(e.target.value)}>
          <option value="">All facilities</option>
          {facilities.map((f) => (
            <option key={f.id} value={f.code}>
              {f.code}
            </option>
          ))}
        </SelectField>
        <label className="check">
          <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
          <span>Unread only</span>
        </label>
      </div>

      {error && <Banner tone="error">{error}</Banner>}

      {loading ? (
        <div className="center">
          <Spinner />
        </div>
      ) : shown.length === 0 ? (
        <EmptyState title={unreadOnly ? "Nothing unread" : "Nothing yet"}>
          {unreadOnly ? "Switch off “Unread only” to see everything." : "Events appear here as they happen."}
        </EmptyState>
      ) : (
        <ul className="events" aria-label="Events">
          {shown.map((e) => {
            const kind = eventLabel(e);
            return (
              <li
                key={e.id}
                className={cx("event", e.severity === "warning" && "event--warning", e.id > lastRead && "event--new")}
              >
                <time className="event__time mono" dateTime={e.created_at}>
                  {formatDateTime(e.created_at)}
                </time>
                <Badge tone={kind.tone}>{kind.label}</Badge>
                <span className="event__summary">
                  {e.summary}
                  {e.actor_name && <span className="event__by"> By {e.actor_name}.</span>}
                </span>
                <span className="event__where mono">{e.facility_code ?? ""}</span>
              </li>
            );
          })}
        </ul>
      )}

      {hasMore && !loading && !unreadOnly && (
        <Button variant="secondary" loading={loadingMore} onClick={() => void loadMore()}>
          Load older
        </Button>
      )}
    </div>
  );
}
