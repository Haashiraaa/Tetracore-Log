// frontend/src/components/ui/TextField.tsx
import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";
import { cx } from "@/lib/cx";

interface FieldChrome {
  label: string;
  hint?: string;
  error?: string | null;
}

function describedBy(id: string, hint?: string, error?: string | null): string | undefined {
  const ids = [hint ? `${id}-hint` : "", error ? `${id}-err` : ""].filter(Boolean);
  return ids.length ? ids.join(" ") : undefined;
}

function Chrome({
  id,
  hint,
  error,
  label,
  children,
}: FieldChrome & { id: string; children: ReactNode }) {
  return (
    <div className={cx("field", error && "field--error")}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint && (
        <p id={`${id}-hint`} className="field__hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-err`} className="field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export const TextField = forwardRef<HTMLInputElement, FieldChrome & InputHTMLAttributes<HTMLInputElement>>(
  function TextField({ label, hint, error, id, className, ...rest }, ref) {
    const auto = useId();
    const fid = id ?? auto;
    return (
      <Chrome id={fid} label={label} hint={hint} error={error}>
        <input
          ref={ref}
          id={fid}
          className={cx("input", className)}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(fid, hint, error)}
          {...rest}
        />
      </Chrome>
    );
  },
);

export function SelectField({
  label,
  hint,
  error,
  id,
  className,
  children,
  ...rest
}: FieldChrome & SelectHTMLAttributes<HTMLSelectElement>) {
  const auto = useId();
  const fid = id ?? auto;
  return (
    <Chrome id={fid} label={label} hint={hint} error={error}>
      <select
        id={fid}
        className={cx("input", "select", className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fid, hint, error)}
        {...rest}
      >
        {children}
      </select>
    </Chrome>
  );
}
