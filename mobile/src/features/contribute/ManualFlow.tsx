/**
 * Type a price in by hand.
 *
 * Product and store are chosen through the shared picker, which explains why
 * the product comes first: it is the only route the API offers to a store id.
 */

import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { ProductSummary } from '../../api/endpoints';
import { useManualReport } from '../../api/queries';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { DecisionCard } from '../../components/DecisionCard';
import { SectionHeader } from '../../components/layout';
import { messageFor } from '../../components/ScreenState';
import { colors, radius, spacing, type as typography } from '../../theme/tokens';
import { StorePicker } from './StorePicker';

type SourceType = 'community' | 'store_visit';

const SOURCE_CHOICES: { value: SourceType; label: string; hint: string }[] = [
  { value: 'store_visit', label: 'I saw it in the store', hint: 'Weighted higher' },
  { value: 'community', label: 'Someone told me', hint: 'Weighted lower' },
];

export function ManualFlow() {
  const [term, setTerm] = useState('');
  const [product, setProduct] = useState<ProductSummary | null>(null);
  const [storeId, setStoreId] = useState<string | null>(null);
  const [price, setPrice] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('store_visit');

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
      <StorePicker
        term={term}
        onTerm={setTerm}
        product={product}
        onProduct={setProduct}
        storeId={storeId}
        onStore={(store) => setStoreId(store?.id ?? null)}
        labels={{
          productTitle: 'Which product?',
          storeTitle: 'Which store?',
          storeHint: 'Stores already pricing this product',
          emptyStores:
            'No store reports this product yet, so there is nowhere to attach a price. A shelf photo is the way in.',
        }}
      />

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
  footnote: {
    ...typography.caption,
    color: colors.textFaint,
    marginTop: spacing.md,
  },
  decision: {
    marginBottom: spacing.lg,
  },
});
