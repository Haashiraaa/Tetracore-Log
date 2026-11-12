// frontend/src/components/entries/EntryTable.tsx
// One table for all three logs. A real table on wide screens; on phones each row
// stacks into a labelled card (see components.css).
import type { AnyEntry } from "@/api/schemas";
import { PlateChip } from "@/components/ui/PlateChip";
import { formatDateTime, formatDuration } from "@/lib/dates";
import { formatScm } from "@/lib/format";
import type { LogKind } from "@/models";
import { faceOf, isTruck } from "@/services/entryService";
import { EntryStatus, signedLabel } from "./EntryStatus";

interface EntryTableProps {
  kind: LogKind;
  entries: AnyEntry[];
  showFacility: boolean;
  onOpen: (entry: AnyEntry) => void;
}

/** How long they were (or have been) inside. A truck counts from entering, and one that left
 *  the queue was never inside. */
function insideFor(e: AnyEntry): string {
  if (isTruck(e)) {
    if (!e.entered_at) return "";
    return formatDuration(e.entered_at, e.signed_out_at ? new Date(e.signed_out_at) : new Date());
  }
  return formatDuration(e.signed_in_at, e.signed_out_at ? new Date(e.signed_out_at) : new Date());
}

export function EntryTable({ kind, entries, showFacility, onOpen }: EntryTableProps) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {kind === "trucks" && <th scope="col">Plate</th>}
            <th scope="col">Full name</th>
            {showFacility && <th scope="col">Facility</th>}
            <th scope="col">In</th>
            <th scope="col">Out</th>
            <th scope="col">{kind === "trucks" ? "On site for" : "Inside for"}</th>
            {kind === "trucks" && <th scope="col">SCM</th>}
            <th scope="col">Signed</th>
            <th scope="col">
              <span className="visually-hidden">Details</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => {
            const face = faceOf(e);
            return (
              <tr key={e.id}>
                {face.plate && (
                  <td data-label="Plate">
                    <PlateChip plate={face.plate} />
                  </td>
                )}
                <td data-label="Full name">
                  <span className="cell-main">{face.name}</span>
                  {face.sub && <span className="cell-sub">{face.sub}</span>}
                  {face.phone && <span className="cell-sub mono">{face.phone}</span>}
                </td>
                {showFacility && (
                  <td data-label="Facility" className="mono">
                    {e.facility_code}
                  </td>
                )}
                <td data-label="In">
                  <span className="mono">{formatDateTime(e.signed_in_at)}</span>
                  <span className="cell-sub">
                    {e.signed_in_by_name}
                    {isTruck(e) && e.status === "queued" ? " (queued)" : e.gate_in ? `, gate ${e.gate_in}` : ""}
                  </span>
                </td>
                <td data-label="Out">
                  {e.signed_out_at ? (
                    <>
                      <span className="mono">{formatDateTime(e.signed_out_at)}</span>
                      {e.signed_out_by_name && (
                        <span className="cell-sub">
                          {e.signed_out_by_name}
                          {e.gate_out ? `, gate ${e.gate_out}` : ""}
                        </span>
                      )}
                      {isTruck(e) && e.status === "left_queue" && (
                        <span className="cell-sub">Left queue: {e.left_queue_reason}</span>
                      )}
                    </>
                  ) : (
                    <EntryStatus entry={e} />
                  )}
                </td>
                <td data-label={kind === "trucks" ? "On site for" : "Inside for"} className="mono">
                  {insideFor(e)}
                </td>
                {kind === "trucks" && (
                  <td data-label="SCM" className="num mono">
                    {isTruck(e) ? formatScm(e.scm_purchased) : ""}
                  </td>
                )}
                <td data-label="Signed" className="mono">
                  {signedLabel(e)}
                </td>
                <td className="table__action">
                  <button type="button" className="btn btn--secondary btn--sm" onClick={() => onOpen(e)}>
                    Details
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
