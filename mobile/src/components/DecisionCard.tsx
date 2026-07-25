/**
 * What the verification gate decided about one submitted price.
 *
 * The reason string comes from the backend and is written to be read by a
 * shopper, so it is shown verbatim rather than being rephrased here.
 */

import { StyleSheet, Text, View } from 'react-native';

import type { EvidenceDecision } from '../api/endpoints';
import { etb, sourceLabel } from '../lib/format';
import { colors, decisionPalette, radius, spacing, type as typography } from '../theme/tokens';
import { DecisionBadge } from './Badge';

const NEXT_STEP: Record<EvidenceDecision['status'], string> = {
  accepted: 'This price is now part of the market estimate.',
  pending: 'It is held for verification until other reports agree.',
  rejected: 'It was not recorded, so the market estimate is unchanged.',
};

export function DecisionCard({ decision }: { decision: EvidenceDecision }) {
  const palette = decisionPalette[decision.status];

  return (
    <View style={[styles.card, { borderColor: palette.fg, backgroundColor: palette.bg }]}>
      <View style={styles.header}>
        <Text style={styles.product} numberOfLines={2}>
          {decision.product_name}
        </Text>
        <DecisionBadge status={decision.status} />
      </View>
      <Text style={styles.price}>
        {etb(decision.price_etb)} ETB - {sourceLabel(decision.source_type)}
      </Text>
      <Text style={styles.reason}>{decision.reason}</Text>
      <Text style={styles.next}>{NEXT_STEP[decision.status]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.lg,
    gap: spacing.xs,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  product: {
    ...typography.bodyStrong,
    color: colors.text,
    flex: 1,
  },
  price: {
    ...typography.body,
    color: colors.text,
  },
  reason: {
    ...typography.caption,
    color: colors.text,
    marginTop: spacing.xs,
  },
  next: {
    ...typography.caption,
    color: colors.textMuted,
  },
});
