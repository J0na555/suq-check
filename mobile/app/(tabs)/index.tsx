/**
 * Market Pulse: the first screen, and the one every launch hits.
 *
 * The recent-verification list at the bottom is deliberate. It shows the gate
 * accepting, holding, and rejecting real submissions, which is what separates
 * SuqCheck from a price list someone typed in.
 */

import { Ionicons } from '@expo/vector-icons';
import { Link } from 'expo-router';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import type { PulseMover } from '../../src/api/endpoints';
import { usePulse, useRecentEvidence } from '../../src/api/queries';
import { Card } from '../../src/components/Card';
import { KeyValue, PageIntro, SectionHeader, StatTile } from '../../src/components/layout';
import { EvidenceRow } from '../../src/components/rows';
import { ErrorState, LoadingState } from '../../src/components/ScreenState';
import { signedPercent } from '../../src/lib/format';
import { colors, radius, spacing, type as typography } from '../../src/theme/tokens';

const MOVER_LABELS: Record<PulseMover['kind'], string> = {
  fastest_rising: 'Rising fastest',
  largest_drop: 'Falling fastest',
  most_stable: 'Most stable',
  most_verified: 'Most verified',
};

export default function PulseScreen() {
  const pulse = usePulse();
  const recent = useRecentEvidence(6);

  if (pulse.isPending) return <LoadingState label="Reading the market" />;
  if (pulse.isError) {
    return <ErrorState error={pulse.error} onRetry={() => void pulse.refetch()} />;
  }

  const { metrics, movers, cheapest_district, most_active_store } = pulse.data;

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={pulse.isRefetching}
          onRefresh={() => {
            void pulse.refetch();
            void recent.refetch();
          }}
          tintColor={colors.brand}
        />
      }
    >
      <PageIntro
        eyebrow="Business intelligence"
        title="Market overview"
        description="Live coverage, price movement, and evidence quality across Addis Ababa."
      />
      <Card>
        <SectionHeader title="Addis Ababa today" hint="Built from verified evidence only" />
        <View style={styles.tiles}>
          <StatTile value={String(metrics.verified_prices_today)} label="Prices verified today" />
          <StatTile value={String(metrics.products_covered)} label="Products covered" />
          <StatTile value={String(metrics.stores_reporting)} label="Stores reporting" />
          <StatTile value={`${metrics.average_confidence}%`} label="Average confidence" />
        </View>
      </Card>

      {movers.length > 0 ? (
        <Card>
          <SectionHeader title="Movers" hint="Change over the last 7 days" />
          {movers.map((mover) => (
            <Link key={`${mover.kind}-${mover.product_id}`} href={`/product/${mover.product_id}`}>
              <View style={styles.mover}>
                <View
                  style={[
                    styles.moverIcon,
                    mover.kind === 'fastest_rising' && styles.moverIconRising,
                  ]}
                >
                  <Ionicons
                    name={mover.kind === 'largest_drop' ? 'trending-down' : 'trending-up'}
                    size={18}
                    color={mover.kind === 'fastest_rising' ? colors.rising : colors.brand}
                  />
                </View>
                <View style={styles.moverText}>
                  <Text style={styles.moverName} numberOfLines={1}>
                    {mover.product_name}
                  </Text>
                  <Text style={styles.moverKind}>{MOVER_LABELS[mover.kind]}</Text>
                </View>
                <Text
                  style={[
                    styles.moverValue,
                    mover.kind === 'fastest_rising' && { color: colors.rising },
                    mover.kind === 'largest_drop' && { color: colors.falling },
                  ]}
                >
                  {mover.kind === 'most_verified'
                    ? mover.display_value
                    : signedPercent(mover.value)}
                </Text>
              </View>
            </Link>
          ))}
        </Card>
      ) : null}

      <Card>
        <SectionHeader title="Where to shop" />
        <View style={styles.signalPanel}>
          <KeyValue label="Cheapest district" value={cheapest_district} />
          <KeyValue label="Most active store" value={most_active_store} />
          <KeyValue label="New receipts today" value={String(metrics.new_receipts_today)} />
        </View>
      </Card>

      <Card>
        <SectionHeader
          title="Latest evidence"
          hint="Every submission, and what the verification gate decided"
        />
        {recent.isPending ? (
          <Text style={styles.pending}>Loading the ingestion feed</Text>
        ) : recent.isError ? (
          <Text style={styles.pending}>The ingestion feed could not be loaded.</Text>
        ) : (
          recent.data.items.map((entry) => <EvidenceRow key={entry.id} entry={entry} />)
        )}
      </Card>

      <Text style={styles.footnote}>
        Every price on SuqCheck is derived from evidence by a deterministic engine. Nothing here is
        typed in by hand, and no single report can move a price on its own.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: spacing.lg,
    gap: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  tiles: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    rowGap: spacing.lg,
    columnGap: spacing.md,
  },
  mover: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  moverIcon: {
    width: 38,
    height: 38,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.brandSoft,
  },
  moverIconRising: {
    backgroundColor: colors.risingSoft,
  },
  moverText: {
    flex: 1,
    gap: 2,
  },
  moverName: {
    ...typography.bodyStrong,
    color: colors.text,
  },
  moverKind: {
    ...typography.caption,
    color: colors.textMuted,
  },
  moverValue: {
    ...typography.bodyStrong,
    color: colors.text,
    fontVariant: ['tabular-nums'],
  },
  pending: {
    ...typography.caption,
    color: colors.textMuted,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.sm,
    padding: spacing.md,
  },
  signalPanel: {
    backgroundColor: colors.surfaceTint,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  footnote: {
    ...typography.caption,
    color: colors.textFaint,
    paddingHorizontal: spacing.xs,
  },
});
