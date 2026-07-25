/** Small layout pieces shared by every screen. */

import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, type as typography } from '../theme/tokens';

export function SectionHeader({
  title,
  hint,
  trailing,
}: {
  title: string;
  hint?: string;
  trailing?: React.ReactNode;
}) {
  return (
    <View style={styles.header}>
      <View style={styles.headerText}>
        <Text style={styles.title}>{title}</Text>
        {hint ? <Text style={styles.hint}>{hint}</Text> : null}
      </View>
      {trailing}
    </View>
  );
}

export function StatTile({ value, label }: { value: string; label: string }) {
  return (
    <View style={styles.tile}>
      <Text style={styles.tileValue} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      <Text style={styles.tileLabel}>{label}</Text>
    </View>
  );
}

export function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.keyValue}>
      <Text style={styles.keyValueLabel}>{label}</Text>
      <Text style={styles.keyValueText}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  headerText: {
    flex: 1,
    gap: 2,
  },
  title: {
    ...typography.heading,
    color: colors.text,
  },
  hint: {
    ...typography.caption,
    color: colors.textMuted,
  },
  tile: {
    flex: 1,
    minWidth: '30%',
    gap: 2,
  },
  tileValue: {
    ...typography.title,
    color: colors.text,
  },
  tileLabel: {
    ...typography.caption,
    color: colors.textMuted,
  },
  keyValue: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
    paddingVertical: spacing.sm,
  },
  keyValueLabel: {
    ...typography.body,
    color: colors.textMuted,
  },
  keyValueText: {
    ...typography.bodyStrong,
    color: colors.text,
  },
});
