/// <reference types="vitest/globals" />

/**
 * Tests for Dashboard mock-data changes (commit e040629).
 *
 * The `withMeta` helper was added to inject `id` and `category` fields
 * into PopularityEntry mock objects, matching the new required fields
 * in the PopularityEntry type.
 *
 * Key behaviors to verify:
 *  - Sequential ids starting from a given startId
 *  - category is injected as 'Bureautique' on all entries
 *  - Original properties (title, popularity_score, etc.) are preserved
 *  - MOCK_ANALYTICS has the correct structure and field types
 */
import { MOCK_ANALYTICS } from '../mock-data'
import type { AnalyticsPopularity } from '@/lib/api'

describe('mock-data – withMeta helper', () => {
  // ── 1. id sequence ──────────────────────────────────────────────────────
  describe('id sequence', () => {
    it('assigns sequential ids starting from 1 for most_popular', () => {
      const ids = MOCK_ANALYTICS.most_popular.map((e) => e.id)
      expect(ids).toEqual([1, 2, 3, 4, 5])
    })

    it('assigns sequential ids starting from 11 for least_popular', () => {
      const ids = MOCK_ANALYTICS.least_popular.map((e) => e.id)
      expect(ids).toEqual([11, 12, 13, 14, 15])
    })

    it('ensures no duplicate ids across both arrays', () => {
      const allIds = [
        ...MOCK_ANALYTICS.most_popular.map((e) => e.id),
        ...MOCK_ANALYTICS.least_popular.map((e) => e.id),
      ]
      const uniqueIds = new Set(allIds)
      expect(uniqueIds.size).toBe(allIds.length)
    })
  })

  // ── 2. category injection ───────────────────────────────────────────────
  describe('category field', () => {
    it('injects category="Bureautique" on every most_popular entry', () => {
      for (const entry of MOCK_ANALYTICS.most_popular) {
        expect(entry.category).toBe('Bureautique')
      }
    })

    it('injects category="Bureautique" on every least_popular entry', () => {
      for (const entry of MOCK_ANALYTICS.least_popular) {
        expect(entry.category).toBe('Bureautique')
      }
    })
  })

  // ── 3. Original properties preserved ────────────────────────────────────
  describe('original properties preserved', () => {
    it('preserves title from the base mock data', () => {
      expect(MOCK_ANALYTICS.most_popular[0]?.title).toBe('Anglais professionnel B2')
      expect(MOCK_ANALYTICS.least_popular[0]?.title).toBe("Initiation à l'IA générative")
    })

    it('preserves popularity_score', () => {
      expect(MOCK_ANALYTICS.most_popular[0]?.popularity_score).toBe(94)
      expect(MOCK_ANALYTICS.least_popular[0]?.popularity_score).toBe(12)
    })

    it('preserves enrolled_count and dropout_count', () => {
      expect(MOCK_ANALYTICS.most_popular[0]?.enrolled_count).toBe(42)
      expect(MOCK_ANALYTICS.most_popular[0]?.dropout_count).toBe(3)
    })

    it('has all 5 entries in each array', () => {
      expect(MOCK_ANALYTICS.most_popular).toHaveLength(5)
      expect(MOCK_ANALYTICS.least_popular).toHaveLength(5)
    })
  })

  // ── 4. Top-level AnalyticsPopularity structure ──────────────────────────
  describe('AnalyticsPopularity structure', () => {
    it('has total_courses, total_enrolled, total_dropouts', () => {
      expect(MOCK_ANALYTICS.total_courses).toBe(47)
      expect(MOCK_ANALYTICS.total_enrolled).toBe(824)
      expect(MOCK_ANALYTICS.total_dropouts).toBe(97)
    })

    it('conforms to the AnalyticsPopularity type (compile-time check)', () => {
      // This assertion ensures MOCK_ANALYTICS satisfies the type contract
      const check: AnalyticsPopularity = MOCK_ANALYTICS
      expect(check).toBeDefined()
    })

    it('each entry conforms to PopularityEntry structure', () => {
      for (const entry of MOCK_ANALYTICS.most_popular) {
        expect(entry).toHaveProperty('id')
        expect(entry).toHaveProperty('title')
        expect(entry).toHaveProperty('category')
        expect(entry).toHaveProperty('popularity_score')
        expect(entry).toHaveProperty('enrolled_count')
        expect(entry).toHaveProperty('dropout_count')
        expect(typeof entry.id).toBe('number')
        expect(typeof entry.title).toBe('string')
        expect(entry.category === null || typeof entry.category === 'string').toBe(true)
        expect(typeof entry.popularity_score).toBe('number')
        expect(typeof entry.enrolled_count).toBe('number')
        expect(typeof entry.dropout_count).toBe('number')
      }
    })
  })
})
