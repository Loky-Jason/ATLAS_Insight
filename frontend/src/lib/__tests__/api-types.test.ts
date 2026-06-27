/// <reference types="vitest/globals" />

/**
 * Compile-time and runtime checks for the PopularityEntry type change
 * (commit e040629).
 */
import type { PopularityEntry, AnalyticsPopularity } from '@/lib/api'

describe('PopularityEntry type', () => {
  it('accepts a valid full entry (all required fields)', () => {
    const entry: PopularityEntry = {
      id: 1,
      title: 'Test Course',
      category: 'Bureautique',
      popularity_score: 85,
      enrolled_count: 30,
      dropout_count: 5,
    }
    expect(entry.id).toBe(1)
    expect(entry.title).toBe('Test Course')
  })

  it('accepts category as null', () => {
    const entry: PopularityEntry = {
      id: 2,
      title: 'Null Category Course',
      category: null,
      popularity_score: 50,
      enrolled_count: 15,
      dropout_count: 2,
    }
    expect(entry.category).toBeNull()
  })

  it('accepts category as a string', () => {
    const entry: PopularityEntry = {
      id: 3,
      title: 'String Category Course',
      category: 'Développement',
      popularity_score: 72,
      enrolled_count: 20,
      dropout_count: 3,
    }
    expect(entry.category).toBe('Développement')
  })

  it('supports AnalyticsPopularity container', () => {
    const data: AnalyticsPopularity = {
      most_popular: [
        { id: 1, title: 'A', category: null, popularity_score: 90, enrolled_count: 10, dropout_count: 1 },
      ],
      least_popular: [
        { id: 2, title: 'B', category: 'Bureautique', popularity_score: 10, enrolled_count: 2, dropout_count: 3 },
      ],
      total_courses: 2,
      total_enrolled: 12,
      total_dropouts: 4,
    }
    expect(data.most_popular).toHaveLength(1)
    expect(data.least_popular).toHaveLength(1)
  })
})
