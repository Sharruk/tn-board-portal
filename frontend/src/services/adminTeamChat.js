import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * Fetch messages for the Admin Team Chat.
 */
export async function getTeamChatMessages({ limit = 50, offset = 0 } = {}) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return apiFetch(`/api/v1/admin/team-chat/messages?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Post a new message to the Admin Team Chat.
 */
export async function sendTeamChatMessage(message) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch('/api/v1/admin/team-chat/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  })
}

