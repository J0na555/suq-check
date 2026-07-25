/**
 * Point the camera at a pack to find it in the catalog.
 *
 * This is a lookup, not a price report: identification only names the product,
 * and the price comes from the evidence already recorded against it.
 */

import { Link } from 'expo-router';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Photo } from '../../src/api/client';
import { useIdentify } from '../../src/api/queries';
import { Button } from '../../src/components/Button';
import { Card } from '../../src/components/Card';
import { KeyValue, PageIntro, SectionHeader } from '../../src/components/layout';
import { PhotoPicker } from '../../src/components/PhotoPicker';
import { messageFor } from '../../src/components/ScreenState';
import { categoryLabel } from '../../src/lib/format';
import { colors, radius, spacing, type as typography } from '../../src/theme/tokens';

const METHOD_LABELS: Record<string, string> = {
  alias_exact: 'Matched a name already in the catalog',
  trigram: 'Matched by close text similarity',
  gemini: 'Matched by Gemini against catalog candidates',
  gemini_vision: 'Read from the photo by Gemini',
  new_product: 'Not in the catalog yet',
};

export default function ScanScreen() {
  const [photo, setPhoto] = useState<Photo | null>(null);
  const identify = useIdentify();
  const result = identify.data;

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <PageIntro
        eyebrow="Visual lookup"
        title="Identify a product"
        description="Photograph the pack and match it against the verified SuqCheck catalog."
      />
      <Card>
        <SectionHeader
          title="1. Capture the label"
          hint="Photograph the front of the pack, label facing you"
        />
        <PhotoPicker
          photo={photo}
          onPhoto={(picked) => {
            setPhoto(picked);
            identify.reset();
          }}
          captureLabel="Photograph a product"
          disabled={identify.isPending}
        />
        {photo ? (
          <View style={styles.submit}>
            <Button
              label={identify.isPending ? 'Reading the label' : 'Identify this product'}
              onPress={() => identify.mutate(photo)}
              busy={identify.isPending}
            />
          </View>
        ) : null}
        {identify.isError ? <Text style={styles.error}>{messageFor(identify.error)}</Text> : null}
      </Card>

      {result ? (
        <Card>
          <SectionHeader title="2. Catalog match" hint="Product identified from the submitted photo" />
          <View style={styles.resultHero}>
            <Text style={styles.resultName}>{result.canonical_name}</Text>
            <Text style={styles.resultBrand}>{result.brand}</Text>
          </View>
          <KeyValue label="Category" value={categoryLabel(result.category)} />
          <KeyValue label="Pack size" value={`${result.size_value} ${result.size_unit}`} />
          <KeyValue
            label="Match confidence"
            value={`${Math.round(result.confidence * 100)}%`}
          />
          <Text style={styles.method}>
            {METHOD_LABELS[result.match_method] ?? result.match_method}
          </Text>

          {result.product_id ? (
            <Link href={`/product/${result.product_id}`} style={styles.link}>
              <Text style={styles.linkLabel}>See its price and confidence</Text>
            </Link>
          ) : (
            <Text style={styles.note}>
              SuqCheck does not track this product yet, so it has no verified price. Photographing a
              shelf tag from the Contribute tab is what adds one.
            </Text>
          )}
        </Card>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: spacing.lg,
    gap: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  submit: {
    marginTop: spacing.md,
  },
  error: {
    ...typography.caption,
    color: colors.danger,
    marginTop: spacing.md,
  },
  method: {
    ...typography.caption,
    marginTop: spacing.sm,
    backgroundColor: colors.infoSoft,
    color: colors.info,
    borderRadius: radius.sm,
    padding: spacing.md,
  },
  link: {
    marginTop: spacing.lg,
  },
  linkLabel: {
    ...typography.bodyStrong,
    color: colors.brand,
  },
  note: {
    ...typography.caption,
    color: colors.textMuted,
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginTop: spacing.lg,
  },
  resultHero: {
    paddingVertical: spacing.md,
    marginBottom: spacing.xs,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  resultName: {
    ...typography.heading,
    color: colors.text,
  },
  resultBrand: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 2,
  },
});
