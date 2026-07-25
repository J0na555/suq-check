import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ManualFlow } from '../../src/features/contribute/ManualFlow';
import { ReceiptFlow } from '../../src/features/contribute/ReceiptFlow';
import { ShelfFlow } from '../../src/features/contribute/ShelfFlow';
import { colors, radius, spacing, type as typography } from '../../src/theme/tokens';

type Mode = 'receipt' | 'shelf' | 'manual';

const MODES: Array<{ value: Mode; label: string }> = [
  { value: 'receipt', label: 'Receipt' },
  { value: 'shelf', label: 'Shelf tag' },
  { value: 'manual', label: 'By hand' },
];

export default function ContributeScreen() {
  const [mode, setMode] = useState<Mode>('receipt');

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
            <Text style={[styles.tabLabel, mode === option.value && styles.tabLabelActive]}>
              {option.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {mode === 'receipt' ? <ReceiptFlow /> : mode === 'shelf' ? <ShelfFlow /> : <ManualFlow />}
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
