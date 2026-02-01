/**
 * Fetch with timeout utility
 * Wraps fetch() to add AbortController-based timeout
 */

export interface FetchWithTimeoutOptions extends RequestInit {
  timeout?: number // timeout in milliseconds
}

/**
 * Fetch with timeout support
 * @param url - The URL to fetch
 * @param options - Fetch options with optional timeout
 * @returns Promise<Response>
 * @throws Error if timeout occurs
 */
export async function fetchWithTimeout(
  url: string,
  options: FetchWithTimeoutOptions = {}
): Promise<Response> {
  const { timeout = 30000, ...fetchOptions } = options
  
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)
  
  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    })
    
    clearTimeout(timeoutId)
    return response
  } catch (error) {
    clearTimeout(timeoutId)
    
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms: ${url}`)
    }
    
    throw error
  }
}

/**
 * Timeout presets for different operations
 */
export const TIMEOUT_PRESETS = {
  SHORT: 10000,      // 10s - quick health checks
  NORMAL: 30000,     // 30s - standard API calls, chat
  LONG: 60000,       // 60s - file uploads, analysis
  VERY_LONG: 120000, // 2m - re-analysis, heavy operations
}

/**
 * Fetch with automatic timeout based on operation type
 */
export async function fetchWithAutoTimeout(
  url: string,
  operationType: keyof typeof TIMEOUT_PRESETS = 'NORMAL',
  options: RequestInit = {}
): Promise<Response> {
  return fetchWithTimeout(url, {
    ...options,
    timeout: TIMEOUT_PRESETS[operationType],
  })
}
