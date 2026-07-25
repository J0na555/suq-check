/**
 * Product detail: the screen the whole demo turns on.
 *
 * It answers four questions in order: what does it cost, how sure are we, why
 * should you believe that, and where is it cheaper. The 30-day change is derived
 * from the history the API already sends rather than asking for another figure.
 */

import { Link, Stack, useLocalSearchParams } from 'expo-router';
import { ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { useProduct } from '../../../src/api/queries';
import { Badge, ConfidenceBadge } from '../../../src/components/Badge';
import { Card } from '../../../src/components/Card';
import { ConfidencePanel } from '../../../src/components/ConfidencePanel';
import { ConfidenceRing } from '../../../src/components/ConfidenceRing';
import { KeyValue, SectionHeader } from '../../../src/components/layout';
import { SourceRow } from '../../../src/components/rows';
import { ErrorState, LoadingState } from '../../../src/components/ScreenState';
import { Sparkline } from '../../../src/components/Sparkline';
import { categoryLabel, dayLabel, etb, signedPercent, timeAgo } from '../../../src/lib/format';
import { colors, radius, spacing, type as typography } from '../../../src/theme/tokens';

export default function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const product = useProduct(id);
  const { width } = useWindowDimensions();

  if (product.isPending) return <LoadingState label="Loading this product" />;
  if (product.isError) {
    return <ErrorState error={product.error} onRetry={() => void product.refetch()} />;
  }

  const detail = product.data;
  const history = detail.history;
  const change =
    history.length >= 2 && history[0].price_etb > 0
      ? (100 * (history[history.length - 1].price_etb - history[0].price_etb)) /
        history[0].price_etb
      : null;
  const chartWidth = Math.max(width - spacing.lg * 4, 120);

  return (
    <>
      <Stack.Screen options={{ title: detail.brand }} />
      <ScrollView contentContainerStyle={styles.content}>
        <Card style={styles.hero}>
          <Text style={styles.eyebrow}>Verified market price</Text>
          <Text style={styles.name}>{detail.canonical_name}</Text>
          <Text style={styles.meta}>
            {categoryLabel(detail.category)} - {detail.size_label}
          </Text>

          <View style={styles.priceRow}>
            <View style={styles.priceBlock}>
              <Text style={styles.price}>{etb(detail.market_price_etb)} ETB</Text>
              <Text style={styles.priceCaption}>
                Market price, updated {timeAgo(detail.updated_at)}
              </Text>
              {change !== null ? (
                <Text
                  style={[
                    styles.change,
                    { color: change > 0 ? colors.rising : change < 0 ? colors.falling : colors.textMuted },
                  ]}
                >
                  {signedPercent(change)} over {history.length} days
                </Text>
              ) : null}
            </View>
            <ConfidenceRing score={detail.confidence} band={detail.confidence_band} />
          </View>

          <View style={styles.badges}>
            <ConfidenceBadge band={detail.confidence_band} score={detail.confidence} />
            <Badge
              label={`${etb(detail.price_range_etb[0])} - ${etb(detail.price_range_etb[1])} ETB seen`}
              foreground={colors.textMuted}
              background={colors.surfaceMuted}
            />
          </View>

          <ConfidencePanel breakdown={detail.confidence_breakdown} />
        </Card>

        {history.length >= 2 ? (
          <Card>
            <SectionHeader
              title="Price history"
              hint={`${dayLabel(history[0].day)} to ${dayLabel(history[history.length - 1].day)}`}
            />
            <Sparkline values={history.map((point) => point.price_etb)} width={chartWidth} />
            <View style={styles.axis}>
              <Text style={styles.axisLabel}>
                {etb(Math.min(...history.map((point) => point.price_etb)))} ETB low
              </Text>
              <Text style={styles.axisLabel}>
                {etb(Math.max(...history.map((point) => point.price_etb)))} ETB high
              </Text>
            </View>
          </Card>
        ) : null}

        <Card>
          <SectionHeader title="Evidence behind this price" />
          <KeyValue label="Accepted reports" value={String(detail.evidence_count)} />
          <KeyValue label="Stores reporting" value={String(detail.store_count)} />
          <KeyValue
            label="Price agreement"
            value={`within ${(detail.spread_pct * 100).toFixed(1)}%`}
          />
          {detail.barcode ? <KeyValue label="Barcode" value={detail.barcode} /> : null}
          <View style={styles.sources}>
            {detail.sources.map((source) => (
              <SourceRow key={source.source_type} source={source} />
            ))}
          </View>
        </Card>

        <Link href={`/product/${detail.id}/stores`} style={styles.link}>
          <Text style={styles.linkLabel}>See stores and prices near you</Text>
        </Link>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: spacing.lg,
    gap: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  name: {
    ...typography.title,
    color: colors.text,
  },
  eyebrow: {
    ...typography.eyebrow,
    color: colors.brand,
    marginBottom: spacing.xs,
  },
  hero: {
    borderTopWidth: 4,
    borderTopColor: colors.brand,
  },
  meta: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.lg,
    marginTop: spacing.lg,
  },
  priceBlock: {
    flex: 1,
    gap: 2,
  },
  price: {
    ...typography.display,
    color: colors.text,
  },
  priceCaption: {
    ...typography.caption,
    color: colors.textMuted,
  },
  change: {
    ...typography.label,
    marginTop: spacing.xs,
  },
  badges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginVertical: spacing.lg,
  },
  axis: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.sm,
  },
  axisLabel: {
    ...typography.caption,
    color: colors.textFaint,
  },
  sources: {
    marginTop: spacing.md,
  },
  link: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.brand,
    borderRadius: radius.md,
  },
  linkLabel: {
    ...typography.bodyStrong,
    color: colors.inverse,
    textAlign: 'center',
  },
});
