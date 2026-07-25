/** Photograph one shelf price tag. The fastest way to add a single price. */

import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { ApiError, type Photo } from '../../api/client';
import { useShelfUpload } from '../../api/queries';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { DecisionCard } from '../../components/DecisionCard';
import { KeyValue, SectionHeader } from '../../components/layout';
import { PhotoPicker } from '../../components/PhotoPicker';
import { messageFor } from '../../components/ScreenState';
import { etb } from '../../lib/format';
import { colors, radius, spacing, type as typography } from '../../theme/tokens';

export function ShelfFlow() {
  const [photo, setPhoto] = useState<Photo | null>(null);
  const upload = useShelfUpload();
  const result = upload.data;
  const notInCatalog = upload.error instanceof ApiError && upload.error.isNotFound;

  return (
    <>
      <Card>
        <SectionHeader title="1. Capture shelf tag" hint="Get the product name and price in frame" />
        <PhotoPicker
          photo={photo}
          onPhoto={(picked) => {
            setPhoto(picked);
            upload.reset();
          }}
          captureLabel="Photograph a price tag"
          disabled={upload.isPending}
        />
        {photo ? (
          <View style={styles.submit}>
            <Button
              label={upload.isPending ? 'Reading the tag' : 'Read this price tag'}
              onPress={() => upload.mutate(photo)}
              busy={upload.isPending}
            />
          </View>
        ) : null}

        {upload.isError ? (
          <Text style={notInCatalog ? styles.note : styles.error}>
            {notInCatalog
              ? `${messageFor(upload.error)} Only tracked products can carry a price, so this tag was not recorded.`
              : messageFor(upload.error)}
          </Text>
        ) : null}
      </Card>

      {result ? (
        <>
          <Card>
            <SectionHeader title="2. Extracted data" />
            <KeyValue label="Tag text" value={result.extraction.raw_product_text} />
            <KeyValue label="Price" value={`${etb(result.extraction.price_etb)} ETB`} />
            <KeyValue
              label="Read quality"
              value={`${Math.round(result.extraction.ocr_confidence * 100)}%`}
            />
            {result.extraction.matched_product_name ? (
              <KeyValue
                label="Matched to"
                value={`${result.extraction.matched_product_name} (${Math.round(
                  result.extraction.match_confidence * 100,
                )}%)`}
              />
            ) : null}
          </Card>

          <Card>
            <SectionHeader title="3. Verification result" />
            <View style={styles.decision}>
              <DecisionCard decision={result.decision} />
            </View>
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
    color: colors.danger,
    marginTop: spacing.md,
  },
  note: {
    ...typography.caption,
    color: colors.textMuted,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  decision: {
    marginTop: spacing.sm,
  },
});
