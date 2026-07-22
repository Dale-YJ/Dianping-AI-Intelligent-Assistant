/**
 * Base HTTP Client
 * ================
 * Wraps the Fetch API with:
 * - Configurable base URL matching the backend (with /v1 prefix)
 * - Request-level timeout
 * - Unified response unwrapping ({ code, message, data } → data)
 *
 * Backend: FastAPI at localhost:8000
 * API docs: ANALYSIS_API_DOCS.md — base path /api/v1
 *
 * Usage (from a module):
 *   import { request } from './client.js'
 *   const data = await request('/chat/send', { method: 'POST', body: {...} })
 */

/* ─── Configuration ─── */
const BASE_URL = '/api/v1'
const DEFAULT_TIMEOUT_MS = 30_000 // RAG / AI summary calls can take a while

/**
 * Thin wrapper around `fetch` with timeout and unified response unwrapping.
 *
 * The backend returns: { code: 0, message: "success", data: {...}, request_id: "uuid" }
 * This function checks `code === 0`, throws on error, and returns `data`.
 *
 * @param {string}  path     - API path, e.g. '/businesses'
 * @param {object}  [opts]
 * @param {string}  [opts.method]  - HTTP method (default 'GET')
 * @param {object}  [opts.params]  - URL query parameters
 * @param {object}  [opts.body]    - JSON request body (only for POST/PUT/PATCH)
 * @param {number}  [opts.timeout] - per-request timeout in ms
 * @returns {Promise<any>} Resolves with the `data` field from the unified response
 * @throws  {Error} On network failure, timeout, non-zero code, or non-2xx HTTP status
 */
export async function request(path, opts = {}) {
  const {
    method = 'GET',
    params,
    body,
    timeout = DEFAULT_TIMEOUT_MS,
  } = opts

  /* Build full URL with query string */
  let url = `${BASE_URL}${path}`
  if (params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') {
        qs.append(k, String(v))
      }
    }
    const qsStr = qs.toString()
    if (qsStr) url += `?${qsStr}`
  }

  /* Build fetch init */
  const init = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    init.body = JSON.stringify(body)
  }

  /* Timeout via AbortController */
  const controller = new AbortController()
  init.signal = controller.signal
  const timer = setTimeout(() => controller.abort(), timeout)

  let response
  try {
    response = await fetch(url, init)
  } catch (err) {
    clearTimeout(timer)
    if (err.name === 'AbortError') {
      throw new Error('请求超时，请检查网络后重试')
    }
    throw new Error(`网络连接失败: ${err.message}`)
  } finally {
    clearTimeout(timer)
  }

  /* Parse JSON body */
  let json
  try {
    json = await response.json()
  } catch {
    if (!response.ok) {
      throw new Error(`服务器返回错误 (HTTP ${response.status})`)
    }
    // Some endpoints may return no body
    return null
  }

  /* Throw on non-2xx HTTP status */
  if (!response.ok) {
    const detail = json.detail || json.message || `HTTP ${response.status}`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  /* Unwrap unified response: { code, message, data, request_id } */
  if (json && typeof json.code === 'number') {
    if (json.code !== 0) {
      throw new Error(json.message || `业务错误 (code=${json.code})`)
    }
    return json.data !== undefined ? json.data : json
  }

  /* Fallback: plain JSON response (e.g. health check at /api/health) */
  return json
}

/* ─── Convenience shorthands ─── */
export const get = (path, params, timeout) =>
  request(path, { method: 'GET', params, timeout })

export const post = (path, body, timeout) =>
  request(path, { method: 'POST', body, timeout })

export const put = (path, body, timeout) =>
  request(path, { method: 'PUT', body, timeout })

export const del = (path, timeout) =>
  request(path, { method: 'DELETE', timeout })
