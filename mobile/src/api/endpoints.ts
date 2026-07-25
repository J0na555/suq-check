/**
 * Every SuqCheck operation, named for what the app wants rather than the route.
 *
 * The types come straight from `contracts/openapi.yaml` via
 * `npm run generate:api`, so a backend schema change breaks the build here
 * instead of at runtime on stage.
 */

import { get, postImage, postJson, type Photo } from './client';
import type { components } from './types';

type Schemas = components['schemas'];

// The backend declares these as Pydantic literal aliases rather than models, so
// FastAPI inlines them and the generator emits no named schema. Reading them off
// the fields that use them keeps them tied to the contract all the same.
export type Category = Schemas['ProductSummary']['category'];
export type ConfidenceBand = Schemas['ProductSummary']['confidence_band'];
export type EvidenceStatus = Schemas['EvidenceLogItem']['status'];
export type SourceType = Schemas['EvidenceLogItem']['source_type'];

export type ConfidenceBreakdown = Schemas['ConfidenceBreakdown'];
export type ConfidenceFactor = Schemas['ConfidenceFactor'];
export type EvidenceDecision = Schemas['EvidenceDecision'];
export type EvidenceLogItem = Schemas['EvidenceLogItem'];
export type EvidenceLogResponse = Schemas['EvidenceLogResponse'];
export type ExtractedLineItem = Schemas['ExtractedLineItem'];
export type HealthResponse = Schemas['HealthResponse'];
export type HistoryPoint = Schemas['HistoryPoint'];
export type ManualEvidenceRequest = Schemas['ManualEvidenceRequest'];
export type ManualEvidenceResponse = Schemas['ManualEvidenceResponse'];
export type NearbyStorePrice = Schemas['NearbyStorePrice'];
export type NearbyStoresResponse = Schemas['NearbyStoresResponse'];
export type PriceListExtraction = Schemas['PriceListExtraction'];
export type PriceListUploadResponse = Schemas['PriceListUploadResponse'];
export type ProductDetail = Schemas['ProductDetail'];
export type ProductIdentification = Schemas['ProductIdentification'];
export type ProductListResponse = Schemas['ProductListResponse'];
export type ProductSummary = Schemas['ProductSummary'];
export type PulseMover = Schemas['PulseMover'];
export type PulseResponse = Schemas['PulseResponse'];
export type ReceiptUploadResponse = Schemas['ReceiptUploadResponse'];
export type ShelfUploadResponse = Schemas['ShelfUploadResponse'];
export type SourceSummary = Schemas['SourceSummary'];
export type StoreDetail = Schemas['StoreDetail'];
export type TrendsResponse = Schemas['TrendsResponse'];

export const health = () => get<HealthResponse>('/healthz');

export const pulse = () => get<PulseResponse>('/api/pulse');

export const searchProducts = (params: {
  q?: string;
  category?: Category | null;
  limit?: number;
  offset?: number;
}) => get<ProductListResponse>('/api/products', params);

export const productDetail = (productId: string) =>
  get<ProductDetail>(`/api/products/${productId}`);

export const productStores = (
  productId: string,
  params: { latitude?: number | null; longitude?: number | null; radius_m?: number } = {},
) => get<NearbyStoresResponse>(`/api/products/${productId}/stores`, params);

export const storeDetail = (storeId: string) => get<StoreDetail>(`/api/stores/${storeId}`);

export const evidenceLog = (params: { status?: EvidenceStatus | null; limit?: number } = {}) =>
  get<EvidenceLogResponse>('/api/evidence', params);

export const trends = (periodDays = 7) =>
  get<TrendsResponse>('/api/analytics/trends', { period_days: periodDays });

export const uploadReceipt = (photo: Photo) =>
  postImage<ReceiptUploadResponse>('/api/evidence/receipt', photo);

export const uploadShelfTag = (photo: Photo) =>
  postImage<ShelfUploadResponse>('/api/evidence/shelf', photo);

export const uploadPriceList = (photo: Photo, storeId: string) =>
  postImage<PriceListUploadResponse>('/api/evidence/price-list', photo, { store_id: storeId });

export const identifyProduct = (photo: Photo) =>
  postImage<ProductIdentification>('/api/scan/identify', photo);

export const reportPrice = (payload: ManualEvidenceRequest) =>
  postJson<ManualEvidenceResponse>('/api/evidence/manual', payload);
