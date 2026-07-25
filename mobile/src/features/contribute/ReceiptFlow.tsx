/**
 * Photograph a receipt, then read back exactly what was extracted and recorded.
 *
 * Lines that matched the catalog are already gated evidence, so this screen
 * reports the decision for each one rather than pretending the shopper still
 * has to confirm it. Lines that matched nothing are shown too, because a
 * shopper seeing an unread line is how the catalog gap gets noticed.
 */

import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { Photo } from '../../api/client';
import { useReceiptUpload } from '../../api/queries';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { DecisionCard } from '../../components/DecisionCard';
import { KeyValue, SectionHeader } from '../../components/layout';
import { PhotoPicker } from '../../components/PhotoPicker';
import { messageFor } from '../../components/ScreenState';
import { etb } from '../../lib/format';
import { colors, radius, spacing, type as typography } from '../../theme/tokens';
import { ExtractionLines } from './ExtractionLines';

export function ReceiptFlow() {
  const [photo, setPhoto] = useState<Photo | null>(null);
  const upload = useReceiptUpload();
  const result = upload.data;

  return (
    <>
      <Card>
        <SectionHeader
          title="Photograph a receipt"
          hint="English or Amharic, printed or handwritten"
        />
        <PhotoPicker
          photo={photo}
          onPhoto={(picked) => {
            setPhoto(picked);
            upload.reset();
          }}
          captureLabel="Photograph a receipt"
          disabled={upload.isPending}
        />
        {photo ? (
          <View style={styles.submit}>
            <Button
              label={upload.isPending ? 'Reading the receipt' : 'Read this receipt'}
              onPress={() => upload.mutate(photo)}
              busy={upload.isPending}
            />
          </View>
        ) : null}
        {upload.isError ? <Text style={styles.error}>{messageFor(upload.error)}</Text> : null}
      </Card>

      {result ? (
        <>
          <Card>
            <SectionHeader title="What we read" hint="Check this against the paper in your hand" />
            {result.extraction.store_name ? (
              <KeyValue label="Store" value={result.extraction.store_name} />
            ) : null}
            {result.extraction.observed_on ? (
              <KeyValue label="Date" value={result.extraction.observed_on} />
            ) : null}
            {result.extraction.total_etb !== null &&
            result.extraction.total_etb !== undefined ? (
              <KeyValue label="Receipt total" value={`${etb(result.extraction.total_etb)} ETB`} />
            ) : null}
            <KeyValue
              label="Read quality"
              value={`${Math.round(result.extraction.ocr_confidence * 100)}%`}
            />

            <ExtractionLines
              items={result.extraction.items}
              emptyNote="Nothing legible was found on that photo. A flatter, brighter shot usually reads."
            />
          </Card>

          <Card>
            <SectionHeader
              title="What the gate decided"
              hint="Each price is checked against the current market estimate"
            />
            {result.decisions.length === 0 ? (
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
        </>
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
});
