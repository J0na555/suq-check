export const CATEGORIES = [
  { value: "", label: "All categories" },
  { value: "cooking_oil", label: "Cooking oil" },
  { value: "sugar", label: "Sugar" },
  { value: "rice", label: "Rice" },
  { value: "flour", label: "Flour" },
  { value: "salt", label: "Salt" },
  { value: "pasta", label: "Pasta" },
  { value: "coffee", label: "Coffee" },
  { value: "tea", label: "Tea" },
  { value: "milk", label: "Milk" },
  { value: "soap", label: "Soap" },
  { value: "detergent", label: "Detergent" },
  { value: "toothpaste", label: "Toothpaste" },
  { value: "shampoo", label: "Shampoo" },
  { value: "bottled_water", label: "Bottled water" },
] as const;

export function categoryLabel(value: string) {
  return (
    CATEGORIES.find((item) => item.value === value)?.label ??
    value.replaceAll("_", " ")
  );
}

export function formatEtb(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} ETB`;
}

export function formatPct(value: number, digits = 1) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}
