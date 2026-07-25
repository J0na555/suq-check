/**
 * Loading, error, and empty states.
 *
 * The API sleeps on a free instance, so the loading copy warns about the first
 * slow request rather than leaving a spinner to look broken.
 */

import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { ApiError, NetworkError } from '../api/client';
import { colors, radius, spacing, type as typography } from '../theme/tokens';

export function LoadingState({ label = 'Loading prices' }: { label?: string }) {
  return (
    <View style={styles.container}>
      <ActivityIndicator color={colors.brand} />
      <Text style={styles.title}>{label}</Text>
      <Text style={styles.body}>The first request after a quiet spell can take a moment.</Text>
    </View>
  );
}

export function EmptyState({ title, body }: { title: string; body?: string }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      {body ? <Text style={styles.body}>{body}</Text> : null}
    </View>
  );
}

export function messageFor(error: unknown): string {
  if (error instanceof ApiError || error instanceof NetworkError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return 'Something went wrong. Try again.';
}

export function ErrorState({
  error,
  onRetry,
  retryLabel = 'Try again',
}: {
  error: unknown;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Not loaded</Text>
      <Text style={styles.body}>{messageFor(error)}</Text>
      {onRetry ? (
        <Pressable
          onPress={onRetry}
          style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
        >
          <Text style={styles.buttonLabel}>{retryLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.xxl,
  },
  title: {
    ...typography.bodyStrong,
    color: colors.text,
  },
  body: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
  },
  button: {
    marginTop: spacing.sm,
    backgroundColor: colors.brand,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
  },
  buttonPressed: {
    backgroundColor: colors.brandDark,
  },
  buttonLabel: {
    ...typography.label,
    color: colors.inverse,
  },
});
