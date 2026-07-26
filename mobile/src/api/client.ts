/**
 * The single place the app talks to SuqCheck.
 *
 * Two things here are not incidental. Every write carries a stable device id,
 * because that is what the backend's rate limiter counts against. And the
 * timeout is generous: the API runs on a free Render instance that sleeps, so
 * the first request after an idle period can take most of a minute.
 */

import { Platform } from 'react-native';

import { deviceId } from './device';

const DEPLOYED_BASE_URL = 'https://suq-check-api.onrender.com';

export const baseUrl = (
  process.env.EXPO_PUBLIC_API_URL?.trim() || DEPLOYED_BASE_URL
).replace(/\/$/, '');

/** A cold Render instance answers in about 50 seconds; anything past this is broken. */
const REQUEST_TIMEOUT_MS = 90_000;

/** Wording for the states the contract documents, so screens never invent their own. */
const MESSAGES: Record<number, string> = {
  404: 'We could not find that in the catalog yet.',
  413: 'That photo is too large. Take another one.',
  415: 'That file is not a JPEG, PNG, or WebP photo.',
  429: 'You have sent a lot of reports. Wait a moment and try again.',
  502: 'The photo could not be read. Try a clearer, straighter shot.',
};

export class ApiError extends Error {
  readonly status: number;
  readonly retryAfterSeconds: number | null;

  constructor(status: number, detail: string | null, retryAfterSeconds: number | null) {
    super(detail || MESSAGES[status] || 'Something went wrong. Try again.');
    this.name = 'ApiError';
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** A retake is worth offering for the states a different photo can fix. */
  get suggestsRetake(): boolean {
    return this.status === 413 || this.status === 415 || this.status === 502;
  }
}

export class NetworkError extends Error {
  constructor(cause?: unknown) {
    super('No connection to SuqCheck. Check your network and try again.');
    this.name = 'NetworkError';
    this.cause = cause;
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

function withQuery(path: string, query?: Query): string {
  if (!query) return `${baseUrl}${path}`;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') {
      search.append(key, String(value));
    }
  }
  const suffix = search.toString();
  return `${baseUrl}${path}${suffix ? `?${suffix}` : ''}`;
}

async function toError(response: Response): Promise<ApiError> {
  let detail: string | null = null;
  try {
    const body = (await response.json()) as { detail?: unknown };
    // FastAPI validation errors put a list here rather than a sentence.
    if (typeof body.detail === 'string') detail = body.detail;
  } catch {
    detail = null;
  }
  const retryAfter = Number(response.headers.get('Retry-After'));
  return new ApiError(response.status, detail, Number.isFinite(retryAfter) ? retryAfter : null);
}

async function send(url: string, init: RequestInit): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(url, { ...init, signal: controller.signal });
  } catch (cause) {
    throw new NetworkError(cause);
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) throw await toError(response);
  return response.status === 204 ? null : ((await response.json()) as unknown);
}

export async function get<Result>(path: string, query?: Query): Promise<Result> {
  return (await send(withQuery(path, query), {
    method: 'GET',
    headers: { Accept: 'application/json' },
  })) as Result;
}

export async function postJson<Result>(path: string, body: unknown): Promise<Result> {
  return (await send(withQuery(path), {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Device-Id': await deviceId(),
    },
    body: JSON.stringify(body),
  })) as Result;
}

export type Photo = {
  uri: string;
  mimeType?: string | null;
  fileName?: string | null;
};

const EXTENSION_TYPES: Record<string, string> = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
};

function photoMeta(photo: Photo): { name: string; type: string } {
  const extension = photo.uri.split('.').pop()?.toLowerCase() ?? '';
  const type = photo.mimeType || EXTENSION_TYPES[extension] || 'image/jpeg';
  const name = photo.fileName || `upload.${type === 'image/png' ? 'png' : 'jpg'}`;
  return { name, type };
}

/**
 * On native, FormData accepts `{ uri, name, type }`. On web, that object is
 * coerced to the string "[object Object]", so FastAPI gets a str instead of a
 * file — fetch the uri into a Blob (or File) and append that instead.
 */
async function appendImage(form: FormData, photo: Photo): Promise<void> {
  const { name, type } = photoMeta(photo);
  if (Platform.OS === 'web') {
    const blob = await fetch(photo.uri).then((r) => r.blob());
    form.append('image', new File([blob], name, { type: blob.type || type }));
    return;
  }
  form.append('image', { uri: photo.uri, name, type } as unknown as Blob);
}

/**
 * Uploads are `multipart/form-data` with a field named `image`. Some carry text
 * fields beside it: a price list is attributed to the store the shopper chose,
 * never to a store guessed from the photo.
 */
export async function postImage<Result>(
  path: string,
  photo: Photo,
  fields: Record<string, string> = {},
): Promise<Result> {
  const form = new FormData();
  await appendImage(form, photo);
  for (const [name, value] of Object.entries(fields)) {
    form.append(name, value);
  }

  return (await send(withQuery(path), {
    method: 'POST',
    headers: { Accept: 'application/json', 'X-Device-Id': await deviceId() },
    body: form,
  })) as Result;
}
