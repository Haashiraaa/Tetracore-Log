// frontend/src/components/entries/KindTabs.tsx
// Trucks / Visitors / Staff switch, used by the Inside and Log pages.
import { LOG_KINDS, LOG_LABEL, type LogKind } from "@/models";

interface KindTabsProps {
  value: LogKind;
  onChange: (kind: LogKind) => void;
  /** Optional number next to each label (e.g. how many are inside). */
  counts?: Partial<Record<LogKind, number>>;
}

export function KindTabs({ value, onChange, counts }: KindTabsProps) {
  return (
    <div className="kind-tabs" role="tablist" aria-label="Which log">
      {LOG_KINDS.map((kind) => (
        <button
          key={kind}
          type="button"
          role="tab"
          aria-selected={value === kind}
          className="kind-tabs__tab"
          onClick={() => onChange(kind)}
        >
          <span>{LOG_LABEL[kind].many}</span>
          {counts?.[kind] !== undefined && <span className="kind-tabs__count">{counts[kind]}</span>}
        </button>
      ))}
    </div>
  );
}
