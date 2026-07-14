/**
 * Base HTTP Client
 * ================
 * Wraps the Fetch API with:
 * - Configurable base URL and default headers
 * - Unified response unwrapping via `code` / `message` / `data`
 * - Business-status-code → Error mapping (400, 404, 422, 500, 1001-1005)
 * - Request-level timeout
 * - Per-request request_id logging for debugging
 *
 * Usage (from a module):
 *   import { request } from './client.js'
 *   const data = await request('/chat/quick-tags')
 */

/* ─── Configuration ─── */
const BASE_URL = '/api/v1'
const DEFAULT_TIMEOUT_MS = 12_000 // generous default; RAG calls take longer

/* ─── Business-error map ─── */
const ERROR_MESSAGES = {
  400: '请求参数有误，请检查输入',
  404: '请求的资源不存在',
  422: 'AI 暂时无法理解您的需求',
  500: '服务器内部异常，请稍后重试',
  1001: '暂未找到匹配的商家',
  1002: '检索超时，请稍后再试',
  1003: 'AI 服务繁忙，请稍后再试',
  1004: '搜索服务异常，请联系管理员',
  1005: '知识库正在更新中，部分功能暂不可用',
}

/**
 * Thin wrapper around `fetch` with timeout and business-error handling.
 *
 * @param {string}  path     - API path, e.g. '/chat/recommend'
 * @param {object}  [opts]
 * @param {string}  [opts.method]  - HTTP method (default 'GET')
 * @param {object}  [opts.params]  - URL query parameters
 * @param {object}  [opts.body]    - JSON request body (only for POST/PUT/PATCH)
 * @param {number}  [opts.timeout] - per-request timeout in ms
 * @returns {Promise<any>} Resolves with the `data` field of the unified response
 * @throws  {ApiError} On any non-zero `code` or network/timeout failure
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
      throw new ApiError(-1, '请求超时，请检查网络后重试', null)
    }
    throw new ApiError(-1, `网络连接失败: ${err.message}`, null)
  } finally {
    clearTimeout(timer)
  }

  /* Parse JSON body */
  let json
  try {
    json = await response.json()
  } catch {
    throw new ApiError(
      response.status,
      `服务器返回了无法解析的响应 (HTTP ${response.status})`,
      null,
    )
  }

  /* Normalise: API doc says every response has {code, message, data, request_id} */
  const { code, message, data, request_id } = json

  /* Success */
  if (code === 0) {
    return data
  }

  /* Non-success business code — throw with a user-friendly message */
  const friendly =
    ERROR_MESSAGES[code] || message || `未知错误 (code: ${code})`
  throw new ApiError(code, friendly, data, request_id)
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

/* ─── Custom Error class ─── */
export class ApiError extends Error {
  /**
   * @param {number} code      - business status code
   * @param {string} message   - human-readable message
   * @param {any}    [data]    - optional payload (e.g. fallback alternatives)
   * @param {string} [requestId]
   */
  constructor(code, message, data, requestId) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.data = data
    this.requestId = requestId || null
  }
}

/**
 * Type-check helper: returns true if the error is a "soft" business error
 * that still returns useful `data` for the UI (e.g. code 1001 with alternatives).
 */
export function isSoftError(err) {
  return err instanceof ApiError && [1001, 1002, 1003, 1004, 1005].includes(err.code)
}
