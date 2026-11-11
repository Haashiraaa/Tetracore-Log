// frontend/src/lib/csv.ts

// Spreadsheet apps run cells starting with = or @ (and +/- followed by a letter) as formulas.
function guard(cell: string): string {
  return /^[=@]|^[+-](?![\d\s.])/.test(cell) ? `'${cell}` : cell;
}

function quote(cell: string): string {
  const safe = guard(cell);
  return /[",\r\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
}

export function toCsv(rows: string[][]): string {
  return rows.map((row) => row.map(quote).join(",")).join("\r\n");
}

export function downloadCsv(filename: string, csv: string): void {
  // BOM so Excel opens UTF-8 correctly.
  const blob = new Blob(["﻿", csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
