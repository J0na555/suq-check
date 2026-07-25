/**
 * The lines Gemini read off a photo, matched and unmatched alike.
 *
 * An unmatched line is shown rather than dropped: a shopper noticing that a
 * line went unread is how a gap in the catalog gets reported.
 */

import { StyleSheet, Text, View } from 'react-native';

import type { ExtractedLineItem } from '../../api/endpoints';
import { etb } from '../../lib/format';
import { colors, radius, spacing, type as typography } from '../../theme/tokens';

export function ExtractionLines({
  items,
  emptyNote,
}: {
  items: ExtractedLineItem[];
  emptyNote: string;
}) {
  if (items.length === 0) {
    return <Text style={styles.note}>{emptyNote}</Text>;
  }

  return (
    <View style={styles.lines}>
      {items.map((line, index) => (
        <View key={`${line.raw_text}-${index}`} style={styles.line}>
          <View style={styles.lineText}>
            <Text style={styles.lineRaw} numberOfLines={1}>
              {line.raw_text}
            </Text>
            <Text style={styles.lineMatch}>
              {line.matched_product_name
                ? `${line.matched_product_name} - ${Math.round(line.match_confidence * 100)}% match`
                : 'Not in the catalog, so it was not recorded'}
            </Text>
          </View>
          <Text style={styles.linePrice}>{etb(line.unit_price_etb)} ETB</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  lines: {
    marginTop: spacing.md,
  },
  line: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  lineText: {
    flex: 1,
    gap: 2,
  },
  lineRaw: {
    ...typography.bodyStrong,
    color: colors.text,
  },
  lineMatch: {
    ...typography.caption,
    color: colors.textMuted,
  },
  linePrice: {
    ...typography.bodyStrong,
    color: colors.text,
  },
  note: {
    ...typography.caption,
    color: colors.textMuted,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginTop: spacing.sm,
  },
});
