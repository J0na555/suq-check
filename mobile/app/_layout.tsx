import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { shouldRetry } from '../src/api/queries';
import { colors } from '../src/theme/tokens';

export default function RootLayout() {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: shouldRetry, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <SafeAreaProvider>
        <StatusBar style="dark" />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: colors.surface },
            headerTitleStyle: { color: colors.text, fontSize: 17, fontWeight: '600' },
            headerTintColor: colors.brand,
            headerShadowVisible: false,
            contentStyle: { backgroundColor: colors.background },
          }}
        >
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="product/[id]/index" options={{ title: 'Product' }} />
          <Stack.Screen name="product/[id]/stores" options={{ title: 'Stores and prices' }} />
          <Stack.Screen name="store/[id]" options={{ title: 'Store' }} />
        </Stack>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
