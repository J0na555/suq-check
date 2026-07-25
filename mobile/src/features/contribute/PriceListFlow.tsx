/**
 * Photograph the price list a shop has posted on its wall.
 *
 * One photo can carry a shop's whole basket, which makes this the cheapest
 * evidence in the app per price recorded. The store is chosen here rather than
 * read off the photo, because attributing a whole list to the wrong shop would
 * poison every price on it.
 *
 * Matched lines land as `store_visit` evidence against the chosen store, so
 * each one passes the gate on its own and gets its own decision.
 */

import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { Photo } from '../../api/client';
import type { NearbyStorePrice, ProductSummary } from '../../api/endpoints';
import { usePriceListUpload } from '../../api/queries';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { DecisionCard } from '../../components/DecisionCard';
import { KeyValue, SectionHeader } from '../../components/layout';
import { PhotoPicker } from '../../components/PhotoPicker';
import { messageFor } from '../../components/ScreenState';
import { colors, radius, spacing, type as typography } from '../../theme/tokens';
import { ExtractionLines } from './ExtractionLines';
import { StorePicker } from './StorePicker';

export function PriceListFlow() {
  const [term, setTerm] = useState('');
  const [product, setProduct] = useState<ProductSummary | null>(null);
  const [store, setStore] = useState<NearbyStorePrice | null>(null);
  const [photo, setPhoto] = useState<Photo | null>(null);
  const upload = usePriceListUpload();
  const result = upload.data;

  const reset = () => {
    setProduct(null);
    setStore(null);
    setTerm('');
    setPhoto(null);
    upload.reset();
  };

  if (result) {
    const recorded = result.decisions.length;
    const read = result.extraction.items.length;

    return (
      <>
        <Card>
          <SectionHeader
            title="What we read"
            hint={`${recorded} of ${read} lines matched the catalog`}
          />
          <KeyValue label="Store" value={result.extraction.store_name} />
          {result.extraction.observed_on ? (
            <KeyValue label="Posted on" value={result.extraction.observed_on} />
          ) : null}
          <KeyValue
            label="Read quality"
            value={`${Math.round(result.extraction.ocr_confidence * 100)}%`}
          />
          <ExtractionLines
            items={result.extraction.items}
            emptyNote="No prices were legible on that photo. Standing square to the board, with the whole list in frame, usually reads."
          />
        </Card>

        <Card>
          <SectionHeader
            title="What the gate decided"
            hint="Every line is checked on its own"
          />
          {recorded === 0 ? (
            <Text style={styles.note}>
              No line matched a tracked product, so nothing was added to the market estimate.
            </Text>
          ) : (
            <View style={styles.decisions}>
              {result.decisions.map((decision) => (
                <DecisionCard key={decision.id} decision={decision} />
              ))}
            </View>
          )}
        </Card>

        <Button label="Photograph another list" variant="secondary" onPress={reset} />
      </>
    );
  }

  return (
    <>
      <StorePicker
        term={term}
        onTerm={setTerm}
        product={product}
        onProduct={setProduct}
        storeId={store?.id ?? null}
        onStore={setStore}
        labels={{
          productTitle: 'Which shop is this list in?',
          productHint: 'Search any item on the board to find the shop',
          storeTitle: 'Pick the shop',
          storeHint: 'Shops already pricing that item',
          emptyStores:
            'No shop is on record for that item, so there is nothing to attach the list to. Try another item from the board.',
        }}
      />

      {store ? (
        <Card>
          <SectionHeader
            title="Photograph the price list"
            hint="Get the whole board in frame, straight on"
          />
          <PhotoPicker
            photo={photo}
            onPhoto={(picked) => {
              setPhoto(picked);
              upload.reset();
            }}
            captureLabel="Photograph the list"
            disabled={upload.isPending}
          />
          {photo ? (
            <View style={styles.submit}>
              <Button
                label={upload.isPending ? 'Reading the list' : 'Read this list'}
                onPress={() => upload.mutate({ photo, storeId: store.id })}
                busy={upload.isPending}
              />
            </View>
          ) : null}
          {upload.isError ? <Text style={styles.error}>{messageFor(upload.error)}</Text> : null}

          <Text style={styles.footnote}>
            Every price on the list is recorded against {store.name} and checked against the market
            estimate, so one photo can move a whole basket.
          </Text>
        </Card>
      ) : null}
    </>
  );
}

const styles = StyleSheet.create({
  submit: {
    marginTop: spacing.md,
  },
  error: {
    ...typography.caption,
    color: colors.low,
    marginTop: spacing.md,
  },
  decisions: {
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  note: {
    ...typography.caption,
    color: colors.textMuted,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginTop: spacing.sm,
  },
  footnote: {
    ...typography.caption,
    color: colors.textFaint,
    marginTop: spacing.md,
  },
});
