/**
 * Energica Configurator — API utility functions.
 *
 * All network calls to the compositor service are routed through this module
 * to keep components free of fetch logic and enable centralized error handling.
 */

// ---------------------------------------------------------------------------
// Types (mirror backend Pydantic models)
// ---------------------------------------------------------------------------

export interface LayerMeta {
  id: string;
  name: string;
  filename: string;
  z_index: number;
  visible_by_default: boolean;
  always_visible: boolean;
  group: string;
}

export interface ConfigRules {
  always_visible: string[];
  mutually_exclusive: string[][];
  dependencies: Record<string, string[]>;
}

export interface ConfigSchema {
  model: string;
  canvas: { width: number; height: number };
  layers: LayerMeta[];
  groups: Record<string, string[]>;
  rules: ConfigRules;
}

export interface ValidateResponse {
  valid: boolean;
  error?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const REQUEST_TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Wraps fetch with an AbortController-based timeout.
 * Throws a descriptive Error on network failure or timeout.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s`);
    }
    throw new Error(`Network error: ${(err as Error).message}`);
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Parse the API error body into a human-readable message.
 */
async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg: string }) => d.msg).join("; ");
    }
    return JSON.stringify(body);
  } catch {
    return `HTTP ${response.status} ${response.statusText}`;
  }
}

// ---------------------------------------------------------------------------
// Config schema — with simple in-process memoisation
// ---------------------------------------------------------------------------

const configCache = new Map<string, ConfigSchema>();

/**
 * Fetch the full layer configuration schema for a model.
 * Responses are memoised in-process for the lifetime of the page.
 */
export async function getModelConfig(
  model: string,
  apiUrl: string,
): Promise<ConfigSchema> {
  const cacheKey = `${apiUrl}:${model}`;
  if (configCache.has(cacheKey)) {
    return configCache.get(cacheKey)!;
  }

  const response = await fetchWithTimeout(`${apiUrl}/config/${model}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Failed to load config for '${model}': ${msg}`);
  }

  const config: ConfigSchema = await response.json();
  configCache.set(cacheKey, config);
  return config;
}

// ---------------------------------------------------------------------------
// Render — with in-flight deduplication
// ---------------------------------------------------------------------------

const inflight = new Map<string, Promise<Blob>>();

/**
 * Render the selected layers into an image and return the result as a Blob.
 * Identical in-flight requests are deduplicated so rapid toggles don't pile up.
 */
export async function renderConfiguration(
  model: string,
  layers: string[],
  apiUrl: string,
  format: "jpeg" | "png" = "jpeg",
): Promise<Blob> {
  const key = `${model}:${[...layers].sort().join(",")}:${format}`;

  if (inflight.has(key)) {
    return inflight.get(key)!;
  }

  const promise = (async (): Promise<Blob> => {
    const response = await fetchWithTimeout(
      `${apiUrl}/configure`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, layers, format, quality: 85 }),
      },
    );

    if (!response.ok) {
      const msg = await extractErrorMessage(response);
      throw new Error(`Render failed: ${msg}`);
    }

    return response.blob();
  })();

  inflight.set(key, promise);

  try {
    const result = await promise;
    return result;
  } finally {
    inflight.delete(key);
  }
}

// ---------------------------------------------------------------------------
// Validate
// ---------------------------------------------------------------------------

/**
 * Validate a layer selection server-side without triggering a full render.
 */
export async function validateConfiguration(
  model: string,
  layers: string[],
  apiUrl: string,
): Promise<ValidateResponse> {
  const response = await fetchWithTimeout(`${apiUrl}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, layers }),
  });

  if (!response.ok) {
    const msg = await extractErrorMessage(response);
    throw new Error(`Validation request failed: ${msg}`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// URL encode / decode helpers
// ---------------------------------------------------------------------------

/**
 * Encode a layer list to a compact base64url string suitable for query params.
 */
export function encodeConfig(layers: string[]): string {
  const sorted = [...layers].sort();
  const json = JSON.stringify(sorted);
  return btoa(json).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/**
 * Decode a base64url config string back to a layer ID array.
 * Returns an empty array if the string is invalid.
 */
export function decodeConfig(encoded: string): string[] {
  try {
    const base64 = encoded.replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(base64);
    const parsed: unknown = JSON.parse(json);
    if (Array.isArray(parsed) && parsed.every((v) => typeof v === "string")) {
      return parsed;
    }
    return [];
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Config cache invalidation (useful in tests / Storybook)
// ---------------------------------------------------------------------------

export function clearConfigCache(): void {
  configCache.clear();
}
