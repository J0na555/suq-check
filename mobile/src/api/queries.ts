/** Query keys and hooks. Reads are cached; writes are always mutations. */

import { useMutation, useQuery, type UseMutationResult } from '@tanstack/react-query';

import { ApiError, type Photo } from './client';
import * as api from './endpoints';

export const keys = {
  pulse: ['pulse'] as const,
  products: (q: string, category: string | null) => ['products', q, category] as const,
  product: (id: string) => ['product', id] as const,
  productStores: (id: string, radius: number) => ['product', id, 'stores', radius] as const,
  store: (id: string) => ['store', id] as const,
  evidence: (status: string | null) => ['evidence', status] as const,
};

/** A missing product is an answer, not a failure worth retrying. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 2;
}

export function usePulse() {
  return useQuery({
    queryKey: keys.pulse,
    queryFn: api.pulse,
    staleTime: 60_000,
    retry: shouldRetry,
  });
}

export function useProductSearch(q: string, category: api.Category | null) {
  return useQuery({
    queryKey: keys.products(q, category),
    queryFn: () => api.searchProducts({ q: q || undefined, category, limit: 50 }),
    staleTime: 30_000,
    retry: shouldRetry,
  });
}

export function useProduct(productId: string) {
  return useQuery({
    queryKey: keys.product(productId),
    queryFn: () => api.productDetail(productId),
    retry: shouldRetry,
  });
}

export function useProductStores(
  productId: string,
  location: { latitude: number; longitude: number } | null,
  radiusM: number,
) {
  return useQuery({
    queryKey: [...keys.productStores(productId, radiusM), location?.latitude ?? null],
    queryFn: () =>
      api.productStores(productId, {
        latitude: location?.latitude,
        longitude: location?.longitude,
        radius_m: location ? radiusM : undefined,
      }),
    // The manual report form mounts this before a product is chosen.
    enabled: productId !== '',
    retry: shouldRetry,
  });
}

export function useStore(storeId: string) {
  return useQuery({
    queryKey: keys.store(storeId),
    queryFn: () => api.storeDetail(storeId),
    retry: shouldRetry,
  });
}

export function useRecentEvidence(limit = 6) {
  return useQuery({
    queryKey: keys.evidence(null),
    queryFn: () => api.evidenceLog({ limit }),
    staleTime: 30_000,
    retry: shouldRetry,
  });
}

export function useReceiptUpload(): UseMutationResult<api.ReceiptUploadResponse, Error, Photo> {
  return useMutation({ mutationFn: api.uploadReceipt });
}

export function useShelfUpload(): UseMutationResult<api.ShelfUploadResponse, Error, Photo> {
  return useMutation({ mutationFn: api.uploadShelfTag });
}

export function usePriceListUpload(): UseMutationResult<
  api.PriceListUploadResponse,
  Error,
  { photo: Photo; storeId: string }
> {
  return useMutation({
    mutationFn: ({ photo, storeId }) => api.uploadPriceList(photo, storeId),
  });
}

export function useIdentify(): UseMutationResult<api.ProductIdentification, Error, Photo> {
  return useMutation({ mutationFn: api.identifyProduct });
}

export function useManualReport(): UseMutationResult<
  api.ManualEvidenceResponse,
  Error,
  api.ManualEvidenceRequest
> {
  return useMutation({ mutationFn: api.reportPrice });
}
