/** Presentation helpers. The API sends raw numbers and ISO strings. */

const CATEGORY_LABELS: Record<string, string> = {
  cooking_oil: 'Cooking oil',
  sugar: 'Sugar',
  rice: 'Rice',
  flour: 'Flour',
  salt: 'Salt',
  pasta: 'Pasta',
  coffee: 'Coffee',
  tea: 'Tea',
  milk: 'Milk',
  soap: 'Soap',
  detergent: 'Detergent',
  toothpaste: 'Toothpaste',
  shampoo: 'Shampoo',
  bottled_water: 'Bottled water',
};

const SOURCE_LABELS: Record<string, string> = {
  partner: 'Partner data',
  receipt: 'Verified receipts',
  scrape: 'Online retailers',
  store_visit: 'Store visits',
  shelf_photo: 'Shelf photos',
  community: 'Community reports',
};

const FACTOR_LABELS: Record<string, string> = {
  volume: 'Volume',
  agreement: 'Agreement',
  freshness: 'Freshness',
  diversity: 'Diversity',
};

export function etb(value: number, { decimals = false }: { decimals?: boolean } = {}): string {
  const rounded = decimals || !Number.isInteger(value) ? value.toFixed(2) : String(value);
  const [whole, fraction] = rounded.split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return fraction ? `${grouped}.${fraction}` : grouped;
}

export function signedPercent(value: number, fractionDigits = 1): string {
  return `${value > 0 ? '+' : ''}${value.toFixed(fractionDigits)}%`;
}

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category.replace(/_/g, ' ');
}

export function sourceLabel(sourceType: string): string {
  return SOURCE_LABELS[sourceType] ?? sourceType.replace(/_/g, ' ');
}

export function factorLabel(name: string): string {
  return FACTOR_LABELS[name] ?? name;
}

export function distance(metres: number | null | undefined): string | null {
  if (metres === null || metres === undefined) return null;
  return metres < 1000 ? `${metres} m` : `${(metres / 1000).toFixed(1)} km`;
}

/** "37 minutes ago", matching the wording the confidence breakdown uses. */
export function timeAgo(iso: string, now: Date = new Date()): string {
  const seconds = Math.max((now.getTime() - new Date(iso).getTime()) / 1000, 0);
  if (seconds < 60) return 'just now';
  const units: Array<[number, string]> = [
    [60, 'minute'],
    [3600, 'hour'],
    [86_400, 'day'],
  ];
  const [divisor, noun] =
    seconds < 3600 ? units[0] : seconds < 86_400 ? units[1] : units[2];
  const count = Math.floor(seconds / divisor);
  return `${count} ${noun}${count === 1 ? '' : 's'} ago`;
}

export function dayLabel(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
}
