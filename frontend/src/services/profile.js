import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * Fetch authenticated user's profile, stats, badge, and leaderboard position.
 */
export async function getMyProfile() {
  const token = await getFirebaseToken()
  if (!token) {
    throw new Error('Authentication required')
  }
  return apiFetch('/api/v1/users/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Update the user's public contribution/display name.
 * @param {string} displayName
 */
export async function updateContributionName(displayName) {
  const token = await getFirebaseToken()
  if (!token) {
    throw new Error('Authentication required')
  }
  return apiFetch('/api/v1/users/me', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ display_name: displayName }),
  })
}
