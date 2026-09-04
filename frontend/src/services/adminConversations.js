import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * Fetch conversations for the Admin Inbox.
 */
export async function getAdminConversations({
  status = null,
  category = null,
  search = '',
  limit = 50,
  offset = 0,
} = {}) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (status) params.append('status', status)
  if (category) params.append('category', category)
  if (search.trim()) params.append('search', search.trim())

  return apiFetch(`/api/v1/admin/conversations?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Fetch inbox conversation lifecycle statistics.
 */
export async function getAdminConversationStats() {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch('/api/v1/admin/conversations/stats', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Open a conversation, mark user messages as read, and retrieve student contribution context.
 */
export async function getAdminConversationDetail(conversationId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch(`/api/v1/admin/conversations/${conversationId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Send an official admin reply in a conversation thread.
 */
export async function sendAdminReply(conversationId, message) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch(`/api/v1/admin/conversations/${conversationId}/reply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  })
}

/**
 * Update conversation lifecycle status (e.g. 'resolved', 'awaiting_admin', etc.).
 */
export async function updateAdminConversationStatus(conversationId, status) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch(`/api/v1/admin/conversations/${conversationId}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ status }),
  })
}
