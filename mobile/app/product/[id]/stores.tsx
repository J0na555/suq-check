/**
 * Where this product is cheaper.
 *
 * Distance only exists once the shopper shares a location: the API measures it
 * server-side from the coordinates it is given, and sorts by price otherwise.
 */

import * as Location from 'expo-location';
import { Stack, useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { useProductStores } from '../../../src/api/queries';
import { Card } from '../../../src/components/Card';
import { KeyValue, SectionHeader } from '../../../src/components/layout';
import { StoreRow } from '../../../src/components/rows';
import { Button } from '../../../src/components/Button';
import { EmptyState, ErrorState, LoadingState } from '../../../src/components/ScreenState';
import { etb } from '../../../src/lib/format';
import { colors, radius, spacing, type as typography } from '../../../src/theme/tokens';

const RADIUS_CHOICES = [500, 2_000, 5_000, 20_000] as const;

type Coordinates = { latitude: number; longitude: number };

export default function ProductStoresScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [location, setLocation] = useState<Coordinates | null>(null);
  const [radiusM, setRadiusM] = useState<number>(5_000);
  const [locationNote, setLocationNote] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);

  const stores = useProductStores(id, location, radiusM);

  const askForLocation = useCallback(async () => {
    setLocating(true);
    setLocationNote(null);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== Location.PermissionStatus.GRANTED) {
        setLocationNote('Without a location, stores are ranked by price instead of distance.');
        return;
      }
      const position = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      setLocation({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      });
    } catch {
      setLocationNote('Your location could not be read, so stores are ranked by price.');
    } finally {
      setLocating(false);
    }
  }, []);

  if (stores.isPending) return <LoadingState label="Comparing stores" />;
  if (stores.isError) {
    return <ErrorState error={stores.error} onRetry={() => void stores.refetch()} />;
  }

  const { items, market_price_etb } = stores.data;
  const cheapest = items.reduce<number | null>(
    (best, store) => (best === null ? store.price_etb : Math.min(best, store.price_etb)),
    null,
  );

  return (
    <>
      <Stack.Screen options={{ title: 'Stores and prices' }} />
      <ScrollView contentContainerStyle={styles.content}>
        <Card>
          <SectionHeader title="Market comparison" />
          <KeyValue label="Market price" value={`${etb(market_price_etb)} ETB`} />
          {cheapest !== null ? (
            <KeyValue label="Cheapest reported" value={`${etb(cheapest)} ETB`} />
          ) : null}
          <KeyValue label="Stores carrying it" value={String(items.length)} />
        </Card>

        <Card>
          <SectionHeader
            title={location ? 'Nearest first' : 'Cheapest first'}
            hint={
              location
                ? 'Measured from your current location'
                : 'Share your location to sort by distance'
            }
          />

          {location ? (
            <View style={styles.radiusStrip}>
              {RADIUS_CHOICES.map((choice) => (
                <Pressable
                  key={choice}
                  onPress={() => setRadiusM(choice)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: radiusM === choice }}
                  style={[styles.radiusChip, radiusM === choice && styles.radiusChipActive]}
                >
                  <Text
                    style={[
                      styles.radiusLabel,
                      radiusM === choice && styles.radiusLabelActive,
                    ]}
                  >
                    {choice < 1000 ? `${choice} m` : `${choice / 1000} km`}
                  </Text>
                </Pressable>
              ))}
            </View>
          ) : (
            <View style={styles.locationPrompt}>
              <Button
                label={locating ? 'Finding you' : 'Use my location'}
                onPress={() => void askForLocation()}
                variant="secondary"
                busy={locating}
              />
            </View>
          )}

          {locationNote ? <Text style={styles.note}>{locationNote}</Text> : null}

          {items.length === 0 ? (
            <EmptyState
              title="No stores in range"
              body="Widen the radius, or report a price yourself from the Contribute tab."
            />
          ) : (
            items.map((store) => <StoreRow key={store.id} store={store} />)
          )}
        </Card>
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
  radiusStrip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  radiusChip: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  radiusChipActive: {
    backgroundColor: colors.brandSoft,
    borderColor: colors.brand,
  },
  radiusLabel: {
    ...typography.label,
    color: colors.textMuted,
  },
  radiusLabelActive: {
    color: colors.brandDark,
  },
  locationPrompt: {
    marginBottom: spacing.md,
  },
  note: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
});
