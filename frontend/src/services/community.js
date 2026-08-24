// =============================================================================
// Community Service — frontend/src/services/community.js
// =============================================================================

import { API_BASE_URL, apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * List community discussion posts (public).
 *
 * @param {number} [page=1]
 * @param {number} [pageSize=20]
 * @returns {Promise<{ data: Array<any>, total: number, page: number, page_size: number, has_next: bool }>}
 */
export async function getCommunityPosts(page = 1, pageSize = 20) {
  return apiFetch(`/api/v1/community/posts?page=${page}&page_size=${pageSize}`)
}

/**
 * Get a single discussion post with comments (public).
 *
 * @param {string} postId
 * @returns {Promise<any>}
 */
export async function getCommunityPost(postId) {
  return apiFetch(`/api/v1/community/posts/${postId}`)
}

/**
 * Create a new discussion post (auth required).
 *
 * @param {{ title: string, content: string }} payload
 * @returns {Promise<any>}
 */
export async function createCommunityPost(payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to create a discussion')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/posts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const b = await res.json()
      detail = b?.detail || b?.message || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return res.json()
}

/**
 * Add a comment to a discussion post (auth required).
 *
 * @param {string} postId
 * @param {{ content: string }} payload
 * @returns {Promise<any>}
 */
export async function addCommunityComment(postId, payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to reply')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/posts/${postId}/comments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const b = await res.json()
      detail = b?.detail || b?.message || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return res.json()
}

/**
 * Toggle upvote on a post (auth required).
 *
 * @param {string} postId
 * @returns {Promise<{ upvotes: number, voted: boolean }>}
 */
export async function togglePostUpvote(postId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to upvote')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/posts/${postId}/upvote`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const b = await res.json()
      detail = b?.detail || b?.message || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return res.json()
}
