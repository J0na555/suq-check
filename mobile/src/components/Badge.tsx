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
};

export function Badge({ label, foreground, background }: BadgeProps) {
  return (
    <View style={[styles.badge, { backgroundColor: background }]}>
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
  return <Badge label={palette.label} foreground={palette.fg} background={palette.bg} />;
}

export function NeutralBadge({ label }: { label: string }) {
  return <Badge label={label} foreground={colors.textMuted} background={colors.surfaceMuted} />;
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: radius.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: 5,
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
  },
});
