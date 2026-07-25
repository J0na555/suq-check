import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import type { Category } from '../api/endpoints';
import { categoryLabel } from '../lib/format';
import { colors, radius, spacing, type as typography } from '../theme/tokens';

export const CATEGORIES: Category[] = [
  'cooking_oil',
  'sugar',
  'rice',
  'flour',
  'salt',
  'pasta',
  'coffee',
  'tea',
  'milk',
  'soap',
  'detergent',
  'toothpaste',
  'shampoo',
  'bottled_water',
];

type Props = {
  selected: Category | null;
  onSelect: (category: Category | null) => void;
};

export function CategoryFilter({ selected, onSelect }: Props) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.strip}
    >
      <Chip label="All" active={selected === null} onPress={() => onSelect(null)} />
      {CATEGORIES.map((category) => (
        <Chip
          key={category}
          label={categoryLabel(category)}
          active={selected === category}
          onPress={() => onSelect(selected === category ? null : category)}
        />
      ))}
    </ScrollView>
  );
}

function Chip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={[styles.chip, active && styles.chipActive]}
    >
      <Text style={[styles.chipLabel, active && styles.chipLabelActive]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  strip: {
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  chip: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  chipActive: {
    backgroundColor: colors.brand,
    borderColor: colors.brand,
  },
  chipLabel: {
    ...typography.label,
    color: colors.textMuted,
  },
  chipLabelActive: {
    color: colors.inverse,
    fontWeight: '600',
  },
});
