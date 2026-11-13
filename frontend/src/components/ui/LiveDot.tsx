// frontend/src/components/ui/LiveDot.tsx
import { useNow } from "@/hooks/useNow";
import { cx } from "@/lib/cx";

function ago(seconds: number): string {
  return seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min`;
}

/** Shows that the screen keeps itself up to date, and how fresh it is. */
export function LiveDot({ updatedAt, failed = false }: { updatedAt: number | null; failed?: boolean }) {
  const now = useNow();
  if (updatedAt === null) return null;
  const seconds = Math.max(0, Math.floor((now - updatedAt) / 1000));
  return (
    <span className={cx("live mono", failed && "live--off")}>
      <span className="live__dot" aria-hidden="true" />
      <span>
        {failed ? "Not updating" : "Live"}
        <span aria-hidden="true"> · checked {ago(seconds)} ago</span>
      </span>
    </span>
  );
}
