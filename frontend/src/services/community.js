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

  return apiFetch('/api/v1/community/posts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
}

/**
 * Update discussion post (author or admin).
 */
export async function updateCommunityPost(postId, payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to update post')

  return apiFetch(`/api/v1/community/posts/${postId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
}

/**
 * Delete post (author or admin).
 */
export async function deleteCommunityPost(postId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to delete post')

  return apiFetch(`/api/v1/community/posts/${postId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
}

/**
 * Add a comment or reply to a discussion post.
 */
export async function addCommunityComment(postId, payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to reply')

  return apiFetch(`/api/v1/community/posts/${postId}/comments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
}

/**
 * Delete comment.
 */
export async function deleteCommunityComment(commentId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to delete reply')

  return apiFetch(`/api/v1/community/comments/${commentId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
}

/**
 * Toggle upvote on a post.
 */
export async function togglePostUpvote(postId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to upvote')

  return apiFetch(`/api/v1/community/posts/${postId}/upvote`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  })
}

/**
 * Submit moderation report.
 */
export async function submitReport(payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to report')

  return apiFetch('/api/v1/community/reports', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
}

/**
 * List moderation reports for admin.
 */
export async function getAdminReports(status = null) {
  const token = await getFirebaseToken()
  const statusParam = status ? `?status=${status}` : ''
  return apiFetch(`/api/v1/community/reports${statusParam}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
}

/**
 * Update report status (admin).
 */
export async function updateAdminReport(reportId, status) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/community/reports/${reportId}?status=${status}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
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

  return apiFetch('/api/v1/community/requests', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
}

export async function updatePaperRequestStatus(requestId, status, fulfilledPaperId = null) {
  const token = await getFirebaseToken()
  const pParam = fulfilledPaperId ? `&fulfilled_paper_id=${fulfilledPaperId}` : ''
  return apiFetch(`/api/v1/community/requests/${requestId}?status=${status}${pParam}`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
}

/**
 * Public User Profile.
 */
export async function getUserProfile(uid) {
  return apiFetch(`/api/v1/community/users/${uid}`)
}
