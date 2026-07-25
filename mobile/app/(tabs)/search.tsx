import { useMemo, useState } from 'react';
import { FlatList, StyleSheet, Text, TextInput, View } from 'react-native';

import type { Category } from '../../src/api/endpoints';
import { useProductSearch } from '../../src/api/queries';
import { CategoryFilter } from '../../src/components/CategoryFilter';
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
      <View style={styles.searchBar}>
        <TextInput
          value={term}
          onChangeText={setTerm}
          placeholder="Search a product or brand"
          placeholderTextColor={colors.textFaint}
          autoCapitalize="none"
          autoCorrect={false}
          returnKeyType="search"
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
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  input: {
    ...typography.body,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radius.md,
    color: colors.text,
    paddingHorizontal: spacing.lg,
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
