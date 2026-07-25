import { Stack, useLocalSearchParams } from 'expo-router';
import { ScrollView, StyleSheet, Text } from 'react-native';

import { useStore } from '../../src/api/queries';
import { Card } from '../../src/components/Card';
import { KeyValue, SectionHeader } from '../../src/components/layout';
import { ErrorState, LoadingState } from '../../src/components/ScreenState';
import { timeAgo } from '../../src/lib/format';
import { colors, spacing, type as typography } from '../../src/theme/tokens';

const KIND_LABELS: Record<string, string> = {
  supermarket: 'Supermarket',
  shop: 'Neighbourhood shop',
  online: 'Online seller',
};

export default function StoreScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const store = useStore(id);

  if (store.isPending) return <LoadingState label="Loading this store" />;
  if (store.isError) {
    return <ErrorState error={store.error} onRetry={() => void store.refetch()} />;
  }

  const detail = store.data;
  const index = detail.average_price_index;
  const verdict =
    index < 98
      ? `Around ${Math.round(100 - index)}% cheaper than the market average`
      : index > 102
        ? `Around ${Math.round(index - 100)}% dearer than the market average`
        : 'Priced in line with the market average';

  return (
    <>
      <Stack.Screen options={{ title: detail.name }} />
      <ScrollView contentContainerStyle={styles.content}>
        <Card>
          <SectionHeader title={detail.name} hint={`${detail.district} - ${KIND_LABELS[detail.kind] ?? detail.kind}`} />
          <KeyValue label="Price index" value={index.toFixed(1)} />
          <KeyValue label="Products priced here" value={String(detail.product_count)} />
          <KeyValue label="Last report" value={timeAgo(detail.last_reported_at)} />
          <Text style={styles.verdict}>{verdict}</Text>
          <Text style={styles.footnote}>
            The index compares this store against the market estimate for the same products, where
            100 is the market average.
          </Text>
        </Card>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: spacing.lg,
    gap: spacing.lg,
  },
  verdict: {
    ...typography.bodyStrong,
    color: colors.text,
    marginTop: spacing.md,
  },
  footnote: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
});
