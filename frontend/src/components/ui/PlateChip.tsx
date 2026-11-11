// frontend/src/components/ui/PlateChip.tsx
// The number plate is the one thing the guard's eyes go to, so it is drawn like one.
import { cx } from "@/lib/cx";

export function PlateChip({ plate, large }: { plate: string; large?: boolean }) {
  return <span className={cx("plate", large && "plate--lg")}>{plate}</span>;
}
