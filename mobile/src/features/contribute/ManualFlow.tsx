/**
 * Type a price in by hand.
 *
 * The store list comes from the stores already pricing the chosen product,
 * because the API has no endpoint that lists stores on their own. That is a
 * genuine constraint, not a design choice, and it is why this form asks for the
 * product first.
 */

import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { ProductSummary } from '../../api/endpoints';
import { useManualReport, useProductSearch, useProductStores } from '../../api/queries';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { DecisionCard } from '../../components/DecisionCard';
import { SectionHeader } from '../../components/layout';
import { messageFor } from '../../components/ScreenState';
import { categoryLabel, etb } from '../../lib/format';
import { useDebounced } from '../../lib/useDebounced';
import { colors, radius, spacing, type as typography } from '../../theme/tokens';

type SourceType = 'community' | 'store_visit';

const SOURCE_CHOICES: Array<{ value: SourceType; label: string; hint: string }> = [
  { value: 'store_visit', label: 'I saw it in the store', hint: 'Weighted higher' },
  { value: 'community', label: 'Someone told me', hint: 'Weighted lower' },
];

export function ManualFlow() {
  const [term, setTerm] = useState('');
  const [product, setProduct] = useState<ProductSummary | null>(null);
  const [storeId, setStoreId] = useState<string | null>(null);
  const [price, setPrice] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('store_visit');

  const query = useDebounced(term, 300);
  const products = useProductSearch(product ? '' : query.trim(), null);
  const stores = useProductStores(product?.id ?? '', null, 5_000);
  const report = useManualReport();

  const priceEtb = Number(price.replace(',', '.'));
  const canSubmit =
    product !== null && storeId !== null && Number.isFinite(priceEtb) && priceEtb > 0;

  const reset = () => {
    setProduct(null);
    setStoreId(null);
    setPrice('');
    setTerm('');
    report.reset();
  };

  if (report.data) {
    return (
      <Card>
        <SectionHeader title="What the gate decided" />
        <View style={styles.decision}>
          <DecisionCard decision={report.data.decision} />
        </View>
        <Button label="Report another price" variant="secondary" onPress={reset} />
      </Card>
    );
  }

  return (
    <>
      <Card>
        <SectionHeader title="Which product?" />
        {product ? (
          <Pressable style={styles.selected} onPress={() => setProduct(null)}>
            <View style={styles.selectedText}>
              <Text style={styles.selectedName}>{product.canonical_name}</Text>
              <Text style={styles.selectedMeta}>
                Market price {etb(product.market_price_etb)} ETB - tap to change
              </Text>
            </View>
          </Pressable>
        ) : (
          <>
            <TextInput
              value={term}
              onChangeText={setTerm}
              placeholder="Search the catalog"
              placeholderTextColor={colors.textFaint}
              autoCapitalize="none"
              autoCorrect={false}
              style={styles.input}
            />
            {products.data?.items.slice(0, 6).map((candidate) => (
              <Pressable
                key={candidate.id}
                style={styles.option}
                onPress={() => {
                  setProduct(candidate);
                  setStoreId(null);
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
          <SectionHeader title="Which store?" hint="Stores already pricing this product" />
          {stores.isPending ? (
            <Text style={styles.note}>Loading stores</Text>
          ) : stores.isError ? (
            <Text style={styles.note}>{messageFor(stores.error)}</Text>
          ) : stores.data.items.length === 0 ? (
            <Text style={styles.note}>
              No store reports this product yet, so there is nowhere to attach a price. A shelf photo
              is the way in.
            </Text>
          ) : (
            stores.data.items.map((store) => (
              <Pressable
                key={store.id}
                style={[styles.option, storeId === store.id && styles.optionActive]}
                onPress={() => setStoreId(store.id)}
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

      {product && storeId ? (
        <Card>
          <SectionHeader title="What did it cost?" />
          <TextInput
            value={price}
            onChangeText={setPrice}
            placeholder="Price in ETB"
            placeholderTextColor={colors.textFaint}
            keyboardType="decimal-pad"
            style={styles.input}
          />

          <View style={styles.sources}>
            {SOURCE_CHOICES.map((choice) => (
              <Pressable
                key={choice.value}
                onPress={() => setSourceType(choice.value)}
                style={[styles.option, sourceType === choice.value && styles.optionActive]}
              >
                <Text style={styles.optionLabel}>{choice.label}</Text>
                <Text style={styles.optionMeta}>{choice.hint}</Text>
              </Pressable>
            ))}
          </View>

          <View style={styles.submit}>
            <Button
              label={report.isPending ? 'Submitting' : 'Submit this price'}
              onPress={() =>
                report.mutate({
                  product_id: product.id,
                  store_id: storeId,
                  price_etb: priceEtb,
                  observed_at: new Date().toISOString(),
                  source_type: sourceType,
                })
              }
              busy={report.isPending}
              disabled={!canSubmit}
            />
          </View>

          {report.isError ? <Text style={styles.error}>{messageFor(report.error)}</Text> : null}

          <Text style={styles.footnote}>
            Your report is checked against the market estimate before it counts. A price far from it
            is held for verification rather than published.
          </Text>
        </Card>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  input: {
    ...typography.body,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.md,
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
    backgroundColor: colors.brandSoft,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  selectedText: {
    gap: 2,
  },
  selectedName: {
    ...typography.bodyStrong,
    color: colors.brandDark,
  },
  selectedMeta: {
    ...typography.caption,
    color: colors.brandDark,
  },
  sources: {
    marginBottom: spacing.md,
  },
  submit: {
    marginTop: spacing.xs,
  },
  error: {
    ...typography.caption,
    color: colors.low,
    marginTop: spacing.md,
  },
  note: {
    ...typography.caption,
    color: colors.textMuted,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.sm,
    padding: spacing.md,
  },
  footnote: {
    ...typography.caption,
    color: colors.textFaint,
    marginTop: spacing.md,
  },
  decision: {
    marginBottom: spacing.lg,
  },
});
