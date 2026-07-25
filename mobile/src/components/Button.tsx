import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { colors, radius, spacing, type as typography } from '../theme/tokens';

type Props = {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary';
  busy?: boolean;
  disabled?: boolean;
};

export function Button({
  label,
  onPress,
  variant = 'primary',
  busy = false,
  disabled = false,
}: Props) {
  const inactive = disabled || busy;
  const secondary = variant === 'secondary';

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: inactive, busy }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.base,
        secondary ? styles.secondary : styles.primary,
        pressed && !inactive && (secondary ? styles.secondaryPressed : styles.primaryPressed),
        inactive && styles.inactive,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={secondary ? colors.brand : colors.inverse} size="small" />
      ) : (
        <Text style={[styles.label, secondary ? styles.secondaryLabel : styles.primaryLabel]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radius.pill,
    minHeight: 48,
    paddingHorizontal: spacing.xl,
  },
  primary: {
    backgroundColor: colors.brand,
  },
  primaryPressed: {
    backgroundColor: colors.brandDark,
  },
  secondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  secondaryPressed: {
    backgroundColor: colors.surfaceMuted,
  },
  inactive: {
    opacity: 0.55,
  },
  label: {
    ...typography.bodyStrong,
  },
  primaryLabel: {
    color: colors.inverse,
  },
  secondaryLabel: {
    color: colors.text,
  },
});
