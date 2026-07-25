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
  chrome: '#073F33',
  chromeSoft: '#0D5948',

  background: '#F6F7F9',
  surface: '#FFFFFF',
  surfaceMuted: '#F1F3F6',
  surfaceTint: '#F8FAFC',

  text: '#111827',
  textMuted: '#6B7280',
  textFaint: '#9CA3AF',
  inverse: '#FFFFFF',

  border: '#E5E7EB',
  borderStrong: '#D1D5DB',
  chartGrid: '#E8ECF1',
  info: '#2676A6',
  infoSoft: '#EAF4FA',
  violet: '#6D5BD0',
  violetSoft: '#F0EDFF',
  amber: '#C47A17',
  amberSoft: '#FFF6E8',

  high: '#0B6E4F',
  highSoft: '#E7F3ED',
  medium: '#B45309',
  mediumSoft: '#FEF3C7',
  low: '#B42318',
  lowSoft: '#FEE4E2',

  rising: '#B42318',
  risingSoft: '#FEE4E2',
  falling: '#0B6E4F',
  danger: '#B42318',
  dangerSoft: '#FEE4E2',
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
  display: { fontSize: 34, fontWeight: '700' as const, letterSpacing: -0.8 },
  title: { fontSize: 22, fontWeight: '700' as const, letterSpacing: -0.35 },
  heading: { fontSize: 17, fontWeight: '600' as const },
  body: { fontSize: 15, fontWeight: '400' as const },
  bodyStrong: { fontSize: 15, fontWeight: '600' as const },
  label: { fontSize: 13, fontWeight: '500' as const },
  caption: { fontSize: 12, fontWeight: '400' as const },
  eyebrow: {
    fontSize: 11,
    fontWeight: '700' as const,
    letterSpacing: 1.5,
    textTransform: 'uppercase' as const,
  },
} as const;

export const shadow = {
  card: {
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  raised: {
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 5,
  },
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
