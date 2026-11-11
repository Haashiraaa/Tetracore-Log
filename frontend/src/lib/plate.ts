// frontend/src/lib/plate.ts
// Mirrors normalize_plate in backend/src/db/orm/_helpers.py: 'abc-123 xy' -> 'ABC123XY'.

export function normalizePlate(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

export function isValidPlate(normalized: string): boolean {
  return normalized.length >= 2 && normalized.length <= 20;
}
