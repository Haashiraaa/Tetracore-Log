// frontend/src/components/entries/Stamp.tsx

/** Lands on a line the moment it is written: "In · 14:32", "Signed out · 15:10". */
export function Stamp({ text }: { text: string }) {
  return (
    <div className="stamp" role="status">
      <span className="stamp__mark">{text}</span>
    </div>
  );
}
