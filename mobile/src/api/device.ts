/**
 * A stable anonymous id for this install.
 *
 * There is no sign-in anywhere in SuqCheck; this header is the only thing tying
 * reports to a submitter, and the backend uses it for rate limiting.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';

const STORAGE_KEY = 'suqcheck.device-id';

let cached: string | null = null;

export async function deviceId(): Promise<string> {
  if (cached) return cached;

  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY);
    if (stored) {
      cached = stored;
      return stored;
    }
  } catch {
    // An unreadable store is not worth failing an upload over.
  }

  const created = Crypto.randomUUID();
  cached = created;
  try {
    await AsyncStorage.setItem(STORAGE_KEY, created);
  } catch {
    // Losing the id only costs this device a fresh rate-limit bucket next launch.
  }
  return created;
}
