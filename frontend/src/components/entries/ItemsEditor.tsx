// frontend/src/components/entries/ItemsEditor.tsx
// "Items brought" for a visitor. Collapsed to a single Add item button until there is
// something to write: a visitor who brought nothing costs no space and no taps. Each tap
// on Add item opens one more name + quantity (+ optional unit) row; a row can be removed again.
import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/Button";
import { uuid } from "@/lib/ids";
import type { ItemRow } from "@/services/visitorService";

interface ItemsEditorProps {
  items: ItemRow[];
  onChange: (items: ItemRow[]) => void;
  disabled?: boolean;
  error?: string | null;
  /** What the list is called: "Items brought" (visitors), "Items delivered" (waybill). */
  label?: string;
}

export function ItemsEditor({ items, onChange, disabled, error, label = "Items brought" }: ItemsEditorProps) {
  const lastName = useRef<HTMLInputElement>(null);
  const grew = useRef(false);

  // After Add item, put the cursor in the new row so the officer can just type.
  useEffect(() => {
    if (grew.current) {
      lastName.current?.focus();
      grew.current = false;
    }
  }, [items.length]);

  const add = () => {
    grew.current = true;
    onChange([...items, { key: uuid(), name: "", quantity: "", unit: "" }]);
  };
  const update = (key: string, patch: Partial<ItemRow>) =>
    onChange(items.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  const remove = (key: string) => onChange(items.filter((row) => row.key !== key));

  return (
    <div className="field items">
      <span className="field__label" id="items-label">
        {label}
      </span>
      {items.length > 0 && (
        <ul className="items__list" aria-labelledby="items-label">
          {items.map((row, i) => (
            <li key={row.key} className="items__row">
              <input
                ref={i === items.length - 1 ? lastName : undefined}
                className="input items__name"
                aria-label={`Item ${i + 1} name`}
                placeholder="Item"
                value={row.name}
                onChange={(e) => update(row.key, { name: e.target.value })}
                autoComplete="off"
                maxLength={100}
                disabled={disabled}
              />
              <input
                className="input items__qty"
                aria-label={`Item ${i + 1} quantity`}
                placeholder="Qty"
                inputMode="numeric"
                value={row.quantity}
                onChange={(e) =>
                  update(row.key, { quantity: e.target.value.replace(/\D/g, "").slice(0, 6) })
                }
                autoComplete="off"
                disabled={disabled}
              />
              <input
                className="input items__unit"
                aria-label={`Item ${i + 1} unit (optional)`}
                placeholder="Unit"
                value={row.unit}
                onChange={(e) => update(row.key, { unit: e.target.value })}
                autoComplete="off"
                maxLength={20}
                disabled={disabled}
              />
              <button
                type="button"
                className="items__remove"
                aria-label={`Remove item ${i + 1}`}
                onClick={() => remove(row.key)}
                disabled={disabled}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <div>
        <Button variant="secondary" size="sm" onClick={add} disabled={disabled}>
          {items.length === 0 ? "+ Add item" : "+ Add another item"}
        </Button>
      </div>
      {error && (
        <p className="field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
