/**
 * Choosing a store, by way of a product.
 *
 * The API has no endpoint that lists stores on their own: the only route to a
 * store id is the list of stores already pricing some product. So both flows
 * that need a store ask for a product first. For a price list that reads
 * oddly until you are standing in front of one, where typing the first line on
 * the board is the fastest way to say which shop you are in.
 *
 * State lives in the parent so a flow can reset it after a submission.
 */

import { Pressable, StyleSheet, Text, TextInput } from 'react-native';

import type { NearbyStorePrice, ProductSummary } from '../../api/endpoints';
import { useProductSearch, useProductStores } from '../../api/queries';
import { Card } from '../../components/Card';
import { SectionHeader } from '../../components/layout';
import { messageFor } from '../../components/ScreenState';
import { categoryLabel, etb } from '../../lib/format';
import { useDebounced } from '../../lib/useDebounced';
import { colors, radius, spacing, type as typography } from '../../theme/tokens';

type Labels = {
  productTitle: string;
  productHint?: string;
  storeTitle: string;
  storeHint?: string;
  emptyStores: string;
};

export function StorePicker({
  term,
  onTerm,
  product,
  onProduct,
  storeId,
  onStore,
  labels,
}: {
  term: string;
  onTerm: (value: string) => void;
  product: ProductSummary | null;
  onProduct: (value: ProductSummary | null) => void;
  storeId: string | null;
  onStore: (value: NearbyStorePrice | null) => void;
  labels: Labels;
}) {
  const query = useDebounced(term, 300);
  const products = useProductSearch(product ? '' : query.trim(), null);
  const stores = useProductStores(product?.id ?? '', null, 5_000);

  return (
    <>
      <Card>
        <SectionHeader title={labels.productTitle} hint={labels.productHint} />
        {product ? (
          <Pressable
            style={styles.selected}
            accessibilityRole="button"
            accessibilityHint="Clears this product selection"
            onPress={() => {
              onProduct(null);
              onStore(null);
            }}
          >
            <Text style={styles.selectedName}>{product.canonical_name}</Text>
            <Text style={styles.selectedMeta}>
              Market price {etb(product.market_price_etb)} ETB - tap to change
            </Text>
          </Pressable>
        ) : (
          <>
            <TextInput
              value={term}
              onChangeText={onTerm}
              placeholder="Search the catalog"
              placeholderTextColor={colors.textFaint}
              autoCapitalize="none"
              autoCorrect={false}
              accessibilityLabel="Search the product catalog"
              style={styles.input}
            />
            {products.data?.items.slice(0, 6).map((candidate) => (
              <Pressable
                key={candidate.id}
                accessibilityRole="button"
                style={styles.option}
                onPress={() => {
                  onProduct(candidate);
                  onStore(null);
                }}
              >
                <Text style={styles.optionLabel}>{candidate.canonical_name}</Text>
                <Text style={styles.optionMeta}>{categoryLabel(candidate.category)}</Text>
              </Pressable>
            ))}
            {query.trim() !== '' && products.data?.items.length === 0 ? (
              <Text style={styles.note}>
                Nothing matches. Only products SuqCheck already tracks can take a report.
              </Text>
            ) : null}
          </>
        )}
      </Card>

      {product ? (
        <Card>
          <SectionHeader title={labels.storeTitle} hint={labels.storeHint} />
          {stores.isPending ? (
            <Text style={styles.note}>Loading stores</Text>
          ) : stores.isError ? (
            <Text style={styles.note}>{messageFor(stores.error)}</Text>
          ) : stores.data.items.length === 0 ? (
            <Text style={styles.note}>{labels.emptyStores}</Text>
          ) : (
            stores.data.items.map((store) => (
              <Pressable
                key={store.id}
                accessibilityRole="button"
                accessibilityState={{ selected: storeId === store.id }}
                style={[styles.option, storeId === store.id && styles.optionActive]}
                onPress={() => onStore(store)}
              >
                <Text style={styles.optionLabel}>{store.name}</Text>
                <Text style={styles.optionMeta}>
                  {store.district} - currently {etb(store.price_etb)} ETB
                </Text>
              </Pressable>
            ))
          )}
        </Card>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  input: {
    ...typography.body,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.borderStrong,
    color: colors.text,
    marginBottom: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  option: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    paddingVertical: spacing.md,
    gap: 2,
  },
  optionActive: {
    backgroundColor: colors.brandSoft,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    borderTopColor: colors.brand,
  },
  optionLabel: {
    ...typography.bodyStrong,
    color: colors.text,
  },
  optionMeta: {
    ...typography.caption,
    color: colors.textMuted,
  },
  selected: {
    backgroundColor: colors.brand,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: 2,
  },
  selectedName: {
    ...typography.bodyStrong,
    color: colors.inverse,
  },
  selectedMeta: {
    ...typography.caption,
    color: colors.brandSoft,
  },
  note: {
    ...typography.caption,
    color: colors.textMuted,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.sm,
    padding: spacing.md,
  },
});
