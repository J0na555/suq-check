import { StyleSheet, Text, View } from 'react-native';

import {
  bandPalette,
  colors,
  decisionPalette,
  radius,
  spacing,
  type ConfidenceBand,
  type DecisionStatus,
} from '../theme/tokens';

type BadgeProps = {
  label: string;
  foreground: string;
  background: string;
  dot?: boolean;
};

export function Badge({ label, foreground, background, dot = false }: BadgeProps) {
  return (
    <View style={[styles.badge, { backgroundColor: background, borderColor: foreground }]}>
      {dot ? <View style={[styles.dot, { backgroundColor: foreground }]} /> : null}
      <Text style={[styles.label, { color: foreground }]}>{label}</Text>
    </View>
  );
}

export function ConfidenceBadge({
  band,
  score,
}: {
  band: ConfidenceBand;
  score?: number;
}) {
  const palette = bandPalette[band];
  return (
    <Badge
      label={score === undefined ? palette.label : `${palette.label} - ${score}`}
      foreground={palette.fg}
      background={palette.bg}
    />
  );
}

export function DecisionBadge({ status }: { status: DecisionStatus }) {
  const palette = decisionPalette[status];
  return <Badge label={palette.label} foreground={palette.fg} background={palette.bg} dot />;
}

export function NeutralBadge({ label }: { label: string }) {
  return <Badge label={label} foreground={colors.textMuted} background={colors.surfaceMuted} />;
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: spacing.md,
    paddingVertical: 5,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: radius.pill,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
  },
});
