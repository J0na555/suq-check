/**
 * One source of truth for colour, spacing, and type.
 *
 * Confidence is the app's central idea, so it gets its own palette: the same
 * three colours are used for a band badge, a ring, and a gate decision, and
 * nothing else in the app is allowed to use them.
 */

export const colors = {
  brand: '#0B6E4F',
  brandDark: '#08533B',
  brandSoft: '#E7F3ED',

  background: '#F6F7F9',
  surface: '#FFFFFF',
  surfaceMuted: '#F1F3F6',

  text: '#111827',
  textMuted: '#6B7280',
  textFaint: '#9CA3AF',
  inverse: '#FFFFFF',

  border: '#E5E7EB',
  borderStrong: '#D1D5DB',

  high: '#0B6E4F',
  highSoft: '#E7F3ED',
  medium: '#B45309',
  mediumSoft: '#FEF3C7',
  low: '#B42318',
  lowSoft: '#FEE4E2',

  rising: '#B42318',
  falling: '#0B6E4F',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
} as const;

export const type = {
  display: { fontSize: 34, fontWeight: '700' as const, letterSpacing: -0.5 },
  title: { fontSize: 22, fontWeight: '700' as const },
  heading: { fontSize: 17, fontWeight: '600' as const },
  body: { fontSize: 15, fontWeight: '400' as const },
  bodyStrong: { fontSize: 15, fontWeight: '600' as const },
  label: { fontSize: 13, fontWeight: '500' as const },
  caption: { fontSize: 12, fontWeight: '400' as const },
} as const;

export type ConfidenceBand = 'high' | 'medium' | 'low';

export const bandPalette: Record<ConfidenceBand, { fg: string; bg: string; label: string }> = {
  high: { fg: colors.high, bg: colors.highSoft, label: 'High confidence' },
  medium: { fg: colors.medium, bg: colors.mediumSoft, label: 'Medium confidence' },
  low: { fg: colors.low, bg: colors.lowSoft, label: 'Low confidence' },
};

export type DecisionStatus = 'accepted' | 'pending' | 'rejected';

export const decisionPalette: Record<DecisionStatus, { fg: string; bg: string; label: string }> = {
  accepted: { fg: colors.high, bg: colors.highSoft, label: 'Accepted' },
  pending: { fg: colors.medium, bg: colors.mediumSoft, label: 'Pending verification' },
  rejected: { fg: colors.low, bg: colors.lowSoft, label: 'Rejected' },
};
