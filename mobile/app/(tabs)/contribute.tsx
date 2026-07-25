import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ManualFlow } from '../../src/features/contribute/ManualFlow';
import { PriceListFlow } from '../../src/features/contribute/PriceListFlow';
import { ReceiptFlow } from '../../src/features/contribute/ReceiptFlow';
import { ShelfFlow } from '../../src/features/contribute/ShelfFlow';
import { colors, radius, spacing, type as typography } from '../../src/theme/tokens';

type Mode = 'receipt' | 'shelf' | 'price_list' | 'manual';

const MODES: { value: Mode; label: string }[] = [
  { value: 'receipt', label: 'Receipt' },
  { value: 'shelf', label: 'Shelf tag' },
  { value: 'price_list', label: 'Price list' },
  { value: 'manual', label: 'By hand' },
];

const FLOWS: Record<Mode, React.ComponentType> = {
  receipt: ReceiptFlow,
  shelf: ShelfFlow,
  price_list: PriceListFlow,
  manual: ManualFlow,
};

export default function ContributeScreen() {
  const [mode, setMode] = useState<Mode>('receipt');
  const Flow = FLOWS[mode];

  return (
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <View style={styles.switcher}>
        {MODES.map((option) => (
          <Pressable
            key={option.value}
            onPress={() => setMode(option.value)}
            accessibilityRole="button"
            accessibilityState={{ selected: mode === option.value }}
            style={[styles.tab, mode === option.value && styles.tabActive]}
          >
            <Text
              style={[styles.tabLabel, mode === option.value && styles.tabLabelActive]}
              numberOfLines={1}
            >
              {option.label}
            </Text>
          </Pressable>
        ))}
      </View>

      <Flow />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: spacing.lg,
    gap: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  switcher: {
    flexDirection: 'row',
    backgroundColor: colors.surfaceMuted,
    borderRadius: radius.pill,
    padding: 4,
    gap: 4,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    borderRadius: radius.pill,
    paddingVertical: spacing.sm,
  },
  tabActive: {
    backgroundColor: colors.surface,
  },
  tabLabel: {
    ...typography.label,
    color: colors.textMuted,
  },
  tabLabelActive: {
    color: colors.text,
  },
});
