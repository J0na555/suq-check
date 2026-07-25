/**
 * The "why should I trust this?" panel.
 *
 * Everything here is read from `confidence_breakdown`, which the price engine
 * persisted when it scored the product. Nothing is recomputed on the device, so
 * what a shopper reads is exactly what the engine decided.
 */

import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { ConfidenceBreakdown } from '../api/endpoints';
import { factorLabel } from '../lib/format';
import { bandPalette, colors, radius, spacing, type as typography } from '../theme/tokens';

export function ConfidencePanel({ breakdown }: { breakdown: ConfidenceBreakdown }) {
  const [open, setOpen] = useState(false);
  const palette = bandPalette[breakdown.band];

  return (
    <View style={styles.container}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        onPress={() => setOpen((wasOpen) => !wasOpen)}
        style={styles.toggle}
      >
        <Text style={styles.toggleLabel}>Why can you trust this price?</Text>
        <Text style={[styles.toggleAction, { color: palette.fg }]}>{open ? 'Hide' : 'Show'}</Text>
      </Pressable>

      {open ? (
        <View style={styles.body}>
          {breakdown.factors.map((factor) => (
            <View key={factor.name} style={styles.factor}>
              <View style={styles.factorHeader}>
                <Text style={styles.factorName}>{factorLabel(factor.name)}</Text>
                <Text style={styles.factorScore}>{factor.score.toFixed(2)}</Text>
              </View>
              <View style={styles.track}>
                <View
                  style={[
                    styles.fill,
                    { width: `${Math.round(factor.score * 100)}%`, backgroundColor: palette.fg },
                  ]}
                />
              </View>
              <Text style={styles.factorDetail}>
                {factor.detail} - {Math.round(factor.weight * 100)}% of the score
              </Text>
            </View>
          ))}

          {breakdown.capped && breakdown.cap_reason ? (
            <Text style={styles.cap}>{breakdown.cap_reason}</Text>
          ) : null}

          <Text style={styles.footnote}>
            Prices come only from evidence: receipts, shelf photos, store visits, partner feeds,
            and community reports. The engine takes a weighted median, so one wrong number cannot
            move it.
          </Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    paddingTop: spacing.md,
  },
  toggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  toggleLabel: {
    ...typography.bodyStrong,
    color: colors.text,
  },
  toggleAction: {
    ...typography.label,
  },
  body: {
    gap: spacing.lg,
    marginTop: spacing.lg,
    backgroundColor: colors.surfaceTint,
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: spacing.md,
  },
  factor: {
    gap: spacing.xs,
  },
  factorHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  factorName: {
    ...typography.label,
    color: colors.text,
  },
  factorScore: {
    ...typography.label,
    color: colors.textMuted,
    fontVariant: ['tabular-nums'],
  },
  track: {
    height: 6,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceMuted,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: radius.pill,
  },
  factorDetail: {
    ...typography.caption,
    color: colors.textMuted,
  },
  cap: {
    ...typography.caption,
    color: colors.medium,
    backgroundColor: colors.mediumSoft,
    borderRadius: radius.sm,
    padding: spacing.md,
  },
  footnote: {
    ...typography.caption,
    color: colors.textFaint,
  },
});
