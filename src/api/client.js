/**
 * Base HTTP Client
 * ================
 * Wraps the Fetch API with:
 * - Configurable base URL matching the backend (no version prefix)
 * - Request-level timeout
 * - Unified error handling
 *
 * Backend: FastAPI at localhost:8000, plain JSON responses (no code/data wrapper).
 *
 * Usage (from a module):
 *   import { request } from './client.js'
 *   const data = await request('/chat/send', { method: 'POST', body: {...} })
 */

/* ─── Configuration ─── */
const BASE_URL = '/api'
const DEFAULT_TIMEOUT_MS = 30_000 // RAG calls can take a while

/**
 * Thin wrapper around `fetch` with timeout.
 *
 * @param {string}  path     - API path, e.g. '/chat/send'
 * @param {object}  [opts]
 * @param {string}  [opts.method]  - HTTP method (default 'GET')
 * @param {object}  [opts.params]  - URL query parameters
 * @param {object}  [opts.body]    - JSON request body (only for POST/PUT/PATCH)
 * @param {number}  [opts.timeout] - per-request timeout in ms
 * @returns {Promise<any>} Resolves with the parsed JSON response body
 * @throws  {Error} On network failure, timeout, or non-2xx HTTP status
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
    // Some endpoints (like DELETE) may return no body
    return null
  }

  /* Throw on non-2xx */
  if (!response.ok) {
    const detail = json.detail || json.message || `HTTP ${response.status}`
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

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
