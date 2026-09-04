import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * Start a new support conversation with TN Board admin.
 */
export async function createConversation({ category, subject, message, submission_id = null }) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch('/api/v1/conversations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      category,
      subject,
      message,
      submission_id,
    }),
  })
}

/**
 * List all conversations opened by the authenticated user.
 */
export async function getMyConversations(limit = 50, offset = 0) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/conversations/me?limit=${limit}&offset=${offset}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Get detailed conversation thread and mark admin messages as read.
 */
export async function getConversationDetail(conversationId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/conversations/${conversationId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Send a reply in an existing conversation thread.
 */
export async function sendConversationMessage(conversationId, message) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  })
}

/**
 * Get unread messages count for current student.
 */
export async function getUnreadConversationCount() {
  const token = await getFirebaseToken()
  if (!token) return { unread_count: 0 }

  return apiFetch('/api/v1/conversations/unread-count', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}
