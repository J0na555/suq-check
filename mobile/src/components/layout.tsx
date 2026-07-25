/** Small layout pieces shared by every screen. */

import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, type as typography } from '../theme/tokens';

export function PageIntro({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <View style={styles.pageIntro}>
      <Text style={styles.eyebrow}>{eyebrow}</Text>
      <Text style={styles.pageTitle}>{title}</Text>
      <Text style={styles.pageDescription}>{description}</Text>
    </View>
  );
}

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
      <View style={styles.tileAccent} />
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
  pageIntro: {
    gap: spacing.xs,
    paddingVertical: spacing.xs,
  },
  eyebrow: {
    ...typography.eyebrow,
    color: colors.brand,
  },
  pageTitle: {
    ...typography.title,
    color: colors.text,
    fontSize: 28,
  },
  pageDescription: {
    ...typography.caption,
    color: colors.textMuted,
    lineHeight: 18,
    maxWidth: 520,
  },
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
    minWidth: '46%',
    gap: 3,
    backgroundColor: colors.surfaceTint,
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: spacing.md,
    overflow: 'hidden',
  },
  tileAccent: {
    position: 'absolute',
    top: 0,
    left: 0,
    bottom: 0,
    width: 3,
    backgroundColor: colors.brand,
  },
  tileValue: {
    ...typography.title,
    color: colors.text,
    fontSize: 24,
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
