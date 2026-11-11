// frontend/src/pages/log/LogPage.tsx
// The full history, for every role (scoped by the server). Facility filtering is
// only offered to people who see all facilities; for everyone else the server
// ignores it anyway.
import { useState, type FormEvent } from "react";
import type { AnyEntry, EntryFilters } from "@/api/schemas";
import { useOfficer } from "@/auth/AuthContext";
import { seesAllFacilities } from "@/auth/permissions";
import { EntryDetailDialog } from "@/components/entries/EntryDetailDialog";
import { EntryTable } from "@/components/entries/EntryTable";
import { KindTabs } from "@/components/entries/KindTabs";
import { Banner } from "@/components/ui/Banner";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { TextField } from "@/components/ui/TextField";
import { PAGE_SIZE } from "@/config/env";
import { errorMessage } from "@/exceptions/errors";
import { useAsync } from "@/hooks/useAsync";
import { downloadCsv } from "@/lib/csv";
import { startOfDayIso, startOfNextDayIso } from "@/lib/dates";
import { LOG_LABEL, type LogKind } from "@/models";
import * as entryService from "@/services/entryService";

interface Draft {
  openOnly: boolean;
  plate: string;
  facility: string;
  from: string; // YYYY-MM-DD
  to: string;
}

const EMPTY: Draft = { openOnly: false, plate: "", facility: "", from: "", to: "" };

function toFilters(d: Draft): EntryFilters {
  return {
    open: d.openOnly || undefined,
    plate: d.plate.trim() || undefined,
    facility_code: d.facility.trim() || undefined,
    date_from: d.from ? startOfDayIso(d.from) : undefined,
    // "to" is inclusive for people, exclusive for the API
    date_to: d.to ? startOfNextDayIso(d.to) : undefined,
  };
}

export default function LogPage() {
  const profile = useOfficer();
  const showFacility = seesAllFacilities(profile);

  const [kind, setKind] = useState<LogKind>("trucks");
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [applied, setApplied] = useState<Draft>(EMPTY);
  const [page, setPage] = useState(0);
  const [formError, setFormError] = useState<string | null>(null);
  const [detail, setDetail] = useState<AnyEntry | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportNote, setExportNote] = useState<{ tone: "success" | "warn" | "error"; text: string } | null>(null);

  const { data, error, loading } = useAsync(
    (signal) => entryService.fetchPage(kind, toFilters(applied), page, signal),
    [kind, applied, page],
  );

  function apply(e: FormEvent) {
    e.preventDefault();
    if (draft.from && draft.to && draft.from > draft.to) {
      setFormError("The From date is after the To date.");
      return;
    }
    setFormError(null);
    setPage(0);
    setApplied({ ...draft });
  }

  function pick(next: LogKind) {
    setKind(next);
    setPage(0);
    setExportNote(null);
  }

  function clearFilters() {
    setFormError(null);
    setDraft(EMPTY);
    setPage(0);
    setApplied(EMPTY);
  }

  async function exportCsv() {
    setExporting(true);
    setExportNote(null);
    try {
      const { rows, capped } = await entryService.fetchAll(kind, toFilters(applied));
      if (rows.length === 0) {
        setExportNote({ tone: "warn", text: "Nothing to export for these filters." });
        return;
      }
      const stamp = new Date().toISOString().slice(0, 10);
      downloadCsv(`${kind}-log-${stamp}.csv`, entryService.entriesToCsv(kind, rows, showFacility));
      setExportNote({
        tone: capped ? "warn" : "success",
        text: capped
          ? `Exported the newest ${rows.length} rows. Narrow the dates to export the rest.`
          : `Exported ${rows.length} ${rows.length === 1 ? "row" : "rows"}.`,
      });
    } catch (e) {
      setExportNote({ tone: "error", text: errorMessage(e) });
    } finally {
      setExporting(false);
    }
  }

  const rows = data?.rows ?? [];
  const first = page * PAGE_SIZE + 1;

  return (
    <div className="page stack stack--lg">
      <PageHeader
        title="The log"
        actions={
          <Button variant="secondary" size="sm" onClick={() => void exportCsv()} loading={exporting}>
            Download CSV
          </Button>
        }
      />

      <KindTabs value={kind} onChange={pick} />

      <form className="card filters" onSubmit={apply} noValidate>
        {kind === "trucks" && (
          <TextField
            label="Plate"
            value={draft.plate}
            onChange={(e) => setDraft({ ...draft, plate: e.target.value.toUpperCase() })}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
          />
        )}
        {showFacility && (
          <TextField
            label="Facility code"
            value={draft.facility}
            onChange={(e) => setDraft({ ...draft, facility: e.target.value.toUpperCase() })}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
          />
        )}
        <TextField
          label="From"
          type="date"
          value={draft.from}
          onChange={(e) => setDraft({ ...draft, from: e.target.value })}
        />
        <TextField
          label="To (included)"
          type="date"
          value={draft.to}
          onChange={(e) => setDraft({ ...draft, to: e.target.value })}
        />
        <label className="check">
          <input
            type="checkbox"
            checked={draft.openOnly}
            onChange={(e) => setDraft({ ...draft, openOnly: e.target.checked })}
          />
          Still inside only
        </label>
        <div className="row filters__actions">
          <Button type="submit">Apply filters</Button>
          <Button variant="ghost" onClick={clearFilters}>
            Clear
          </Button>
        </div>
        {formError && <Banner tone="error">{formError}</Banner>}
      </form>

      {exportNote && <Banner tone={exportNote.tone}>{exportNote.text}</Banner>}
      {error !== null && <Banner tone="error">{errorMessage(error)}</Banner>}
      {loading && data === null && error === null && <Spinner />}

      {data !== null && rows.length === 0 && (
        <EmptyState title="No entries found">
          {page > 0 ? "That page is empty." : `No ${LOG_LABEL[kind].many.toLowerCase()} entries match these filters yet.`}
        </EmptyState>
      )}

      {rows.length > 0 && (
        <>
          <EntryTable kind={kind} entries={rows} showFacility={showFacility} onOpen={setDetail} />
          <div className="row row--between">
            <span className="muted">
              Showing {first} to {first + rows.length - 1}
            </span>
            <div className="row">
              <Button variant="secondary" size="sm" disabled={page === 0 || loading} onClick={() => setPage(page - 1)}>
                Newer
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={!data?.hasMore || loading}
                onClick={() => setPage(page + 1)}
              >
                Older
              </Button>
            </div>
          </div>
        </>
      )}

      <EntryDetailDialog kind={kind} entry={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
