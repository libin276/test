const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    let detail = '请求失败'
    try {
      const errorBody = await response.json()
      detail = errorBody.detail || detail
    } catch {
      detail = response.statusText || detail
    }
    throw new Error(detail)
  }

  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

function buildQuery(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return
    }
    if (Array.isArray(value)) {
      value.filter(Boolean).forEach((item) => searchParams.append(key, item))
      return
    }
    searchParams.append(key, String(value))
  })
  const queryString = searchParams.toString()
  return queryString ? `?${queryString}` : ''
}

export function getServers(params) {
  return request(`/api/servers${buildQuery(params)}`)
}

export function createServer(payload) {
  return request('/api/servers', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateServer(id, payload) {
  return request(`/api/servers/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function toggleServer(id, enabled) {
  return request(`/api/servers/${id}/enable`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  })
}

export function deleteServer(id) {
  return request(`/api/servers/${id}`, {
    method: 'DELETE',
  })
}

export function getTopics(params) {
  return request(`/api/topics${buildQuery(params)}`)
}

export function createTopic(payload) {
  return request('/api/topics', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateTopic(id, payload) {
  return request(`/api/topics/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function toggleTopic(id, enabled) {
  return request(`/api/topics/${id}/enable`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  })
}

export function deleteTopic(id) {
  return request(`/api/topics/${id}`, {
    method: 'DELETE',
  })
}

export function getMessages(params) {
  return request(`/api/messages${buildQuery(params)}`)
}

export function getRuntimeStatus() {
  return request('/api/runtime')
}

export function getMessageTrend() {
  return request('/api/stat/message_trend')
}

export function getTopicRank() {
  return request('/api/stat/topic_rank')
}

export function getDeviceRank() {
  return request('/api/stat/device_rank')
}

export function getSettings() {
  return request('/api/settings')
}

export function updateSettings(payload) {
  return request('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function buildExportUrl(params) {
  return `${API_BASE_URL}/api/messages/export${buildQuery(params)}`
}
