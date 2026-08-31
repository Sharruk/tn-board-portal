// =============================================================================
// Community Service — frontend/src/services/community.js
// =============================================================================

import { API_BASE_URL, apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

export const COMMUNITY_CATEGORIES = [
  'All',
  'Question Papers',
  'Exams',
  'Study Help',
  'Announcements',
  'Suggestions',
  'General Discussion',
  'Discussion',
  'Question',
]

export const CATEGORY_ICONS = {
  'Question Papers': '📚',
  Exams: '📝',
  'Study Help': '🎓',
  Announcements: '📢',
  Suggestions: '💡',
  'General Discussion': '❓',
  Discussion: '💬',
  Question: '❓',
  'Paper Request': '📄',
  Suggestion: '💡',
  'Problem Report': '⚠️',
  All: '🌐',
}


/**
 * List community discussion posts with optional category filter.
 */
export async function getCommunityPosts(category = 'All', page = 1, pageSize = 20) {
  const catQuery = category && category !== 'All' ? `&category=${encodeURIComponent(category)}` : ''
  return apiFetch(`/api/v1/community/posts?page=${page}&page_size=${pageSize}${catQuery}`)
}

/**
 * Get a single discussion post with threaded comments.
 */
export async function getCommunityPost(postId) {
  return apiFetch(`/api/v1/community/posts/${postId}`)
}

/**
 * Create a new discussion post (auth required).
 */
export async function createCommunityPost(payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to create a post')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/posts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to create post')
  }

  return res.json()
}

/**
 * Update post (author or admin).
 */
export async function updateCommunityPost(postId, payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to update post')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/posts/${postId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to update post')
  }

  return res.json()
}

/**
 * Delete post (author or admin).
 */
export async function deleteCommunityPost(postId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to delete post')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/posts/${postId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to delete post')
  }

  return res.json()
}

/**
 * Add a comment or reply to a discussion post.
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
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to post reply')
  }

  return res.json()
}

/**
 * Delete comment.
 */
export async function deleteCommunityComment(commentId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to delete reply')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/comments/${commentId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })

  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to delete reply')
  }

  return res.json()
}

/**
 * Toggle upvote on a post.
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
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to upvote')
  }

  return res.json()
}

/**
 * Submit moderation report.
 */
export async function submitReport(payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to report')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/reports`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to submit report')
  }

  return res.json()
}

/**
 * List moderation reports for admin.
 */
export async function getAdminReports(status = null) {
  const token = await getFirebaseToken()
  const statusParam = status ? `?status=${status}` : ''
  const res = await fetch(`${API_BASE_URL}/api/v1/community/reports${statusParam}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to load reports')
  }
  return res.json()
}

/**
 * Update report status (admin).
 */
export async function updateAdminReport(reportId, status) {
  const token = await getFirebaseToken()
  const res = await fetch(`${API_BASE_URL}/api/v1/community/reports/${reportId}?status=${status}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to update report')
  }
  return res.json()
}

/**
 * Paper Requests.
 */
export async function getPaperRequests(status = null, page = 1, pageSize = 20) {
  const st = status ? `&status=${status}` : ''
  return apiFetch(`/api/v1/community/requests?page=${page}&page_size=${pageSize}${st}`)
}

export async function createPaperRequest(payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to request a paper')

  const res = await fetch(`${API_BASE_URL}/api/v1/community/requests`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to submit paper request')
  }

  return res.json()
}

export async function updatePaperRequestStatus(requestId, status, fulfilledPaperId = null) {
  const token = await getFirebaseToken()
  const pParam = fulfilledPaperId ? `&fulfilled_paper_id=${fulfilledPaperId}` : ''
  const res = await fetch(`${API_BASE_URL}/api/v1/community/requests/${requestId}?status=${status}${pParam}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
  if (!res.ok) {
    const b = await res.json().catch(() => ({}))
    throw new Error(b?.detail || 'Failed to update request')
  }
  return res.json()
}

/**
 * Public User Profile.
 */
export async function getUserProfile(uid) {
  return apiFetch(`/api/v1/community/users/${uid}`)
}
