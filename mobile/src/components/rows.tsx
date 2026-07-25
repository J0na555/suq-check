/** The repeated list rows: products, stores, evidence sources, ingestion entries. */

import { Ionicons } from '@expo/vector-icons';
import { Link } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type {
  EvidenceLogItem,
  NearbyStorePrice,
  ProductSummary,
  SourceSummary,
} from '../api/endpoints';
import { categoryLabel, distance, etb, sourceLabel, timeAgo } from '../lib/format';
import { colors, radius, spacing, type as typography } from '../theme/tokens';
import { ConfidenceBadge, DecisionBadge, NeutralBadge } from './Badge';

export function ProductRow({ product }: { product: ProductSummary }) {
  return (
    <Link href={`/product/${product.id}`} asChild>
      <Pressable style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}>
        <View style={styles.rowText}>
          <Text style={styles.rowTitle} numberOfLines={1}>
            {product.canonical_name}
          </Text>
          <Text style={styles.rowMeta}>
            {categoryLabel(product.category)} - {product.size_label}
          </Text>
        </View>
        <View style={styles.rowTrailing}>
          <Text style={styles.price}>{etb(product.market_price_etb)} ETB</Text>
          <ConfidenceBadge band={product.confidence_band} score={product.confidence} />
        </View>
        <Ionicons name="chevron-forward" color={colors.textFaint} size={16} />
      </Pressable>
    </Link>
  );
}

const VERDICT_COPY = {
  cheap: { label: 'Cheapest here', color: colors.falling },
  fair: { label: 'Around market', color: colors.textMuted },
  high: { label: 'Above market', color: colors.rising },
} as const;

export function StoreRow({ store }: { store: NearbyStorePrice }) {
  const verdict = VERDICT_COPY[store.verdict];
  const away = distance(store.distance_m);
  const difference = store.difference_from_market_etb;

  return (
    <Link href={`/store/${store.id}`} asChild>
      <Pressable style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}>
        <View style={styles.rowText}>
          <Text style={styles.rowTitle} numberOfLines={1}>
            {store.name}
          </Text>
          <Text style={styles.rowMeta}>
            {[store.district, away, timeAgo(store.updated_at)].filter(Boolean).join(' - ')}
          </Text>
        </View>
        <View style={styles.rowTrailing}>
          <Text style={styles.price}>{etb(store.price_etb)} ETB</Text>
          <Text style={[styles.verdict, { color: verdict.color }]}>
            {difference === 0
              ? verdict.label
              : `${difference > 0 ? '+' : '-'}${etb(Math.abs(difference))} ETB`}
          </Text>
        </View>
        <Ionicons name="chevron-forward" color={colors.textFaint} size={16} />
      </Pressable>
    </Link>
  );
}

export function SourceRow({ source }: { source: SourceSummary }) {
  return (
    <View style={styles.staticRow}>
      <View style={styles.rowText}>
        <Text style={styles.rowTitle}>{sourceLabel(source.source_type)}</Text>
        <Text style={styles.rowMeta}>Newest {timeAgo(source.newest_observed_at)}</Text>
      </View>
      <NeutralBadge
        label={`${source.count} ${source.count === 1 ? 'report' : 'reports'}`}
      />
    </View>
  );
}

export function EvidenceRow({ entry }: { entry: EvidenceLogItem }) {
  return (
    <View style={styles.evidenceRow}>
      <View style={styles.evidenceHeader}>
        <Text style={styles.rowTitle} numberOfLines={1}>
          {entry.product_name}
        </Text>
        <DecisionBadge status={entry.status} />
      </View>
      <Text style={styles.rowMeta}>
        {etb(entry.price_etb)} ETB - {sourceLabel(entry.source_type)}
        {entry.store_name ? ` - ${entry.store_name}` : ''} - {timeAgo(entry.created_at)}
      </Text>
      {entry.rejection_reason ? (
        <Text style={styles.reason}>{entry.rejection_reason}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    borderRadius: radius.md,
    shadowColor: colors.text,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  rowPressed: {
    backgroundColor: colors.surfaceMuted,
  },
  staticRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowText: {
    flex: 1,
    gap: 2,
  },
  rowTrailing: {
    alignItems: 'flex-end',
    gap: spacing.xs,
  },
  rowTitle: {
    ...typography.bodyStrong,
    color: colors.text,
  },
  rowMeta: {
    ...typography.caption,
    color: colors.textMuted,
  },
  price: {
    ...typography.bodyStrong,
    color: colors.text,
  },
  verdict: {
    ...typography.caption,
    fontWeight: '600',
  },
  evidenceRow: {
    gap: spacing.xs,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  evidenceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  reason: {
    ...typography.caption,
    backgroundColor: colors.mediumSoft,
    color: colors.medium,
    borderRadius: radius.sm,
    padding: spacing.sm,
  },
});
