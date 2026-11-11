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

function insideFor(e: AnyEntry): string {
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
            <th scope="col">Inside for</th>
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
                  <span className="cell-sub">{e.signed_in_by_name}</span>
                </td>
                <td data-label="Out">
                  {e.signed_out_at ? (
                    <>
                      <span className="mono">{formatDateTime(e.signed_out_at)}</span>
                      {e.signed_out_by_name && <span className="cell-sub">{e.signed_out_by_name}</span>}
                    </>
                  ) : (
                    <EntryStatus entry={e} />
                  )}
                </td>
                <td data-label="Inside for" className="mono">
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
