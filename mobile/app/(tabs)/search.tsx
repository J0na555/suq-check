import { Ionicons } from '@expo/vector-icons';
import { useMemo, useState } from 'react';
import { FlatList, StyleSheet, Text, TextInput, View } from 'react-native';

import type { Category } from '../../src/api/endpoints';
import { useProductSearch } from '../../src/api/queries';
import { CategoryFilter } from '../../src/components/CategoryFilter';
import { PageIntro } from '../../src/components/layout';
import { EmptyState, ErrorState, LoadingState } from '../../src/components/ScreenState';
import { ProductRow } from '../../src/components/rows';
import { useDebounced } from '../../src/lib/useDebounced';
import { colors, radius, spacing, type as typography } from '../../src/theme/tokens';

export default function SearchScreen() {
  const [term, setTerm] = useState('');
  const [category, setCategory] = useState<Category | null>(null);
  const query = useDebounced(term, 300);
  const products = useProductSearch(query.trim(), category);

  const summary = useMemo(() => {
    if (!products.data) return null;
    const { total } = products.data;
    return `${total} ${total === 1 ? 'product' : 'products'}`;
  }, [products.data]);

  return (
    <View style={styles.screen}>
      <View style={styles.intro}>
        <PageIntro
          eyebrow="Price discovery"
          title="Find a product"
          description="Search current market prices and compare confidence at a glance."
        />
      </View>
      <View style={styles.searchBar}>
        <Ionicons name="search" color={colors.textFaint} size={19} />
        <TextInput
          value={term}
          onChangeText={setTerm}
          placeholder="Search a product or brand"
          placeholderTextColor={colors.textFaint}
          autoCapitalize="none"
          autoCorrect={false}
          returnKeyType="search"
          accessibilityLabel="Search products and brands"
          style={styles.input}
        />
      </View>

      <CategoryFilter selected={category} onSelect={setCategory} />

      {products.isPending ? (
        <LoadingState label="Searching" />
      ) : products.isError ? (
        <ErrorState error={products.error} onRetry={() => void products.refetch()} />
      ) : products.data.items.length === 0 ? (
        <EmptyState
          title="Nothing matches yet"
          body="Only products with accepted evidence carry a price. Try another spelling, or report a price from the Contribute tab."
        />
      ) : (
        <FlatList
          data={products.data.items}
          keyExtractor={(product) => product.id}
          renderItem={({ item }) => <ProductRow product={item} />}
          contentContainerStyle={styles.list}
          ListHeaderComponent={summary ? <Text style={styles.summary}>{summary}</Text> : null}
          keyboardShouldPersistTaps="handled"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.background,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginHorizontal: spacing.lg,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    ...{
      shadowColor: colors.text,
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.05,
      shadowRadius: 6,
      elevation: 2,
    },
  },
  intro: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
  },
  input: {
    ...typography.body,
    flex: 1,
    color: colors.text,
    paddingVertical: spacing.md,
  },
  list: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  summary: {
    ...typography.caption,
    color: colors.textMuted,
    paddingVertical: spacing.sm,
  },
});
