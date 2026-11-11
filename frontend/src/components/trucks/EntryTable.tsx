// frontend/src/components/trucks/EntryTable.tsx
// A real table on wide screens; on phones each row stacks into a labelled card (see components.css).
import type { TruckEntry } from "@/api/schemas";
import { PlateChip } from "@/components/ui/PlateChip";
import { formatDateTime } from "@/lib/dates";
import { formatScm } from "@/lib/format";
import { EntryStatus } from "./EntryStatus";

interface EntryTableProps {
  entries: TruckEntry[];
  showFacility: boolean;
  onOpen: (entry: TruckEntry) => void;
}

export function EntryTable({ entries, showFacility, onOpen }: EntryTableProps) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Plate</th>
            {showFacility && <th scope="col">Facility</th>}
            <th scope="col">Driver</th>
            <th scope="col">Signed in</th>
            <th scope="col">Signed out</th>
            <th scope="col">SCM</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="visually-hidden">Details</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id}>
              <td data-label="Plate">
                <PlateChip plate={e.plate_number} />
              </td>
              {showFacility && <td data-label="Facility">{e.facility_code}</td>}
              <td data-label="Driver">
                <span className="cell-main">{e.driver_name}</span>
                {e.company && <span className="cell-sub">{e.company}</span>}
              </td>
              <td data-label="Signed in">
                {formatDateTime(e.signed_in_at)}
                <span className="cell-sub">{e.signed_in_by_name}</span>
              </td>
              <td data-label="Signed out">
                {e.signed_out_at ? (
                  <>
                    {formatDateTime(e.signed_out_at)}
                    {e.signed_out_by_name && <span className="cell-sub">{e.signed_out_by_name}</span>}
                  </>
                ) : (
                  "—"
                )}
              </td>
              <td data-label="SCM" className="num">
                {formatScm(e.scm_purchased)}
              </td>
              <td data-label="Status">
                <EntryStatus entry={e} />
              </td>
              <td className="table__action">
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => onOpen(e)}>
                  Details
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
