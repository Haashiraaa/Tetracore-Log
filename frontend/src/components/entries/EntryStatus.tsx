// frontend/src/components/entries/EntryStatus.tsx
import type { AnyEntry } from "@/api/schemas";
import { Badge } from "@/components/ui/Badge";

/** Text plus colour, so the state never depends on colour alone. */
export function EntryStatus({ entry }: { entry: AnyEntry }) {
  return entry.signed_out_at ? <Badge tone="grey">Out</Badge> : <Badge tone="amber">Inside</Badge>;
}

/** "in + out", "in only", "out only" or "none": which signatures the entry has. */
export function signedLabel(entry: AnyEntry): string {
  if (entry.has_signature && entry.has_signature_out) return "in + out";
  if (entry.has_signature) return "in only";
  if (entry.has_signature_out) return "out only";
  return "none";
}
