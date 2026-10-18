// frontend/src/components/ui/Spinner.tsx
import { cx } from "@/lib/cx";

export function Spinner({ small, label = "Loading" }: { small?: boolean; label?: string }) {
  return (
    <span
      className={cx("spinner", small && "spinner--small")}
      role={small ? undefined : "status"}
      aria-label={small ? undefined : label}
      aria-hidden={small ? true : undefined}
    />
  );
}
