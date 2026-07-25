/** Take or choose a photo, preview it, and hand it to whoever needs to upload. */

import { useState } from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';

import type { Photo } from '../api/client';
import { choosePhoto, PermissionDenied, takePhoto } from '../lib/photo';
import { colors, radius, spacing, type as typography } from '../theme/tokens';
import { Button } from './Button';

type Props = {
  photo: Photo | null;
  onPhoto: (photo: Photo | null) => void;
  captureLabel?: string;
  disabled?: boolean;
};

export function PhotoPicker({
  photo,
  onPhoto,
  captureLabel = 'Take a photo',
  disabled = false,
}: Props) {
  const [problem, setProblem] = useState<string | null>(null);

  const run = async (source: 'camera' | 'library') => {
    setProblem(null);
    try {
      const picked = source === 'camera' ? await takePhoto() : await choosePhoto();
      if (picked) onPhoto(picked);
    } catch (error) {
      setProblem(
        error instanceof PermissionDenied
          ? error.message
          : 'That photo could not be opened. Try another one.',
      );
    }
  };

  return (
    <View style={styles.container}>
      {photo ? (
        <Image source={{ uri: photo.uri }} style={styles.preview} resizeMode="cover" />
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>
            Fill the frame with the receipt or price tag, and keep it flat.
          </Text>
        </View>
      )}

      <View style={styles.actions}>
        <View style={styles.action}>
          <Button
            label={photo ? 'Retake' : captureLabel}
            onPress={() => void run('camera')}
            disabled={disabled}
          />
        </View>
        <View style={styles.action}>
          <Button
            label="Choose photo"
            variant="secondary"
            onPress={() => void run('library')}
            disabled={disabled}
          />
        </View>
      </View>

      {problem ? <Text style={styles.problem}>{problem}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.md,
  },
  preview: {
    width: '100%',
    height: 220,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceMuted,
  },
  placeholder: {
    height: 220,
    borderRadius: radius.md,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.borderStrong,
    backgroundColor: colors.surfaceMuted,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  placeholderText: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  action: {
    flex: 1,
  },
  problem: {
    ...typography.caption,
    color: colors.low,
  },
});
