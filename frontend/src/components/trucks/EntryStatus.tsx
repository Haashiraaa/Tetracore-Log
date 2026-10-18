// frontend/src/components/trucks/EntryStatus.tsx
import type { TruckEntry } from "@/api/schemas";
import { Badge } from "@/components/ui/Badge";

/** Text plus colour, so the state never depends on colour alone. */
export function EntryStatus({ entry }: { entry: TruckEntry }) {
  return entry.signed_out_at ? <Badge tone="green">Out</Badge> : <Badge tone="amber">Inside</Badge>;
}
