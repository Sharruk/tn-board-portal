// =============================================================================
// Leaderboard Service — frontend/src/services/leaderboard.js
// =============================================================================

import { apiFetch } from '../lib/api'

/**
 * Fetch the public contributor leaderboard rankings.
 *
 * @param {number} [limit=50]  Max contributors to return
 * @returns {Promise<{ data: Array<{ rank: number, contributor_name: string, total_contributions: number, accepted_contributions: number, acceptance_rate: number }>, total_contributors: number }>}
 */
export async function getLeaderboard(limit = 50) {
  return apiFetch(`/api/v1/leaderboard?limit=${limit}`)
}
