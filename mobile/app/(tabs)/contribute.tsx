import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ManualFlow } from '../../src/features/contribute/ManualFlow';
import { PriceListFlow } from '../../src/features/contribute/PriceListFlow';
import { ReceiptFlow } from '../../src/features/contribute/ReceiptFlow';
import { ShelfFlow } from '../../src/features/contribute/ShelfFlow';
import { PageIntro } from '../../src/components/layout';
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
      <PageIntro
        eyebrow="Evidence pipeline"
        title="Report a price"
        description="Choose the strongest evidence available. Every submission passes through the verification gate."
      />
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
    borderRadius: radius.md,
    padding: 4,
    gap: 4,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    borderRadius: radius.sm,
    paddingVertical: spacing.sm,
  },
  tabActive: {
    backgroundColor: colors.brand,
  },
  tabLabel: {
    ...typography.label,
    color: colors.textMuted,
  },
  tabLabelActive: {
    color: colors.inverse,
    fontWeight: '600',
  },
});
