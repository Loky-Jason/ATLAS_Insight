/// <reference types="vitest/globals" />

/**
 * Compile-time and runtime checks for the PopularityEntry type change
 * (commit e040629) and Phase 1b types (commits 55caafb + 68850d7).
 */
import type {
  PopularityEntry,
  AnalyticsPopularity,
  SchoolRegistry,
  SchoolCourse,
  ScanRun,
  ScanDiff,
  DashboardCounts,
  GapRecommendationList,
} from '@/lib/api'
import { dashboardApi, gapApi } from '@/lib/api'

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

// ── Phase 1b types ──────────────────────────────────────────────────────────

describe('SchoolRegistry type', () => {
  it('accepts a valid object with all fields', () => {
    const school: SchoolRegistry = {
      id: 1,
      name: 'École de test',
      url: 'https://example.com',
      scraper_strategy: 'stub',
      active: true,
      scan_interval: 1440,
      last_scanned_at: null,
      config: null,
      created_at: '2026-06-01T00:00:00Z',
    }
    expect(school.name).toBe('École de test')
    expect(school.scan_interval).toBe(1440)
  })

  it('accepts last_scanned_at as null (never scanned)', () => {
    const school: SchoolRegistry = {
      id: 2,
      name: 'New School',
      url: 'https://new.example.com',
      scraper_strategy: 'SCAP',
      active: false,
      scan_interval: 60,
      last_scanned_at: null,
      config: null,
      created_at: '2026-06-15T00:00:00Z',
    }
    expect(school.last_scanned_at).toBeNull()
  })

  it('accepts a non-null last_scanned_at', () => {
    const school: SchoolRegistry = {
      id: 3,
      name: 'Scanned School',
      url: 'https://scanned.example.com',
      scraper_strategy: 'stub',
      active: true,
      scan_interval: 1440,
      last_scanned_at: '2026-06-27T12:00:00Z',
      config: { mode: 'sitemap', sitemap_url: 'auto' },
      created_at: '2026-06-01T00:00:00Z',
    }
    expect(school.last_scanned_at).toBe('2026-06-27T12:00:00Z')
  })
})

describe('SchoolCourse type', () => {
  it('accepts a valid object with all nullable fields', () => {
    const course: SchoolCourse = {
      id: 1,
      school_registry_id: 1,
      external_id: 'ext-abc-123',
      title: 'Introduction à Python',
      url: null,
      description: null,
      duration_hours: null,
      price: null,
      category: null,
      format: null,
      certification: null,
      first_seen_at: '2026-06-01T00:00:00Z',
      last_seen_at: '2026-06-27T00:00:00Z',
      last_updated_at: null,
      is_removed: false,
      removed_at: null,
    }
    expect(course.title).toBe('Introduction à Python')
    expect(course.is_removed).toBe(false)
  })

  it('accepts a fully populated course', () => {
    const course: SchoolCourse = {
      id: 2,
      school_registry_id: 1,
      external_id: 'ext-xyz-456',
      title: 'IA Générative Avancée',
      url: 'https://example.com/course/456',
      description: 'Un cours avancé sur les LLMs',
      duration_hours: 40,
      price: 299.99,
      category: 'Développement',
      format: 'présentiel',
      certification: 'Certificat IA',
      first_seen_at: '2026-06-01T00:00:00Z',
      last_seen_at: '2026-06-27T00:00:00Z',
      last_updated_at: '2026-06-20T00:00:00Z',
      is_removed: false,
      removed_at: null,
    }
    expect(course.price).toBe(299.99)
    expect(course.duration_hours).toBe(40)
  })

  it('accepts a removed course', () => {
    const course: SchoolCourse = {
      id: 3,
      school_registry_id: 1,
      external_id: 'ext-old',
      title: 'Old Course',
      url: null,
      description: null,
      duration_hours: null,
      price: null,
      category: null,
      format: null,
      certification: null,
      first_seen_at: '2026-01-01T00:00:00Z',
      last_seen_at: '2026-06-01T00:00:00Z',
      last_updated_at: null,
      is_removed: true,
      removed_at: '2026-06-15T00:00:00Z',
    }
    expect(course.is_removed).toBe(true)
    expect(course.removed_at).not.toBeNull()
  })
})

describe('ScanRun type', () => {
  it('accepts a completed scan run', () => {
    const run: ScanRun = {
      id: 1,
      school_registry_id: 1,
      status: 'completed',
      started_at: '2026-06-27T10:00:00Z',
      finished_at: '2026-06-27T10:05:00Z',
      courses_found: 42,
      courses_new: 5,
      courses_removed: 2,
      courses_modified: 3,
      error_msg: null,
    }
    expect(run.status).toBe('completed')
    expect(run.courses_found).toBe(42)
  })

  it('accepts a running scan', () => {
    const run: ScanRun = {
      id: 2,
      school_registry_id: 1,
      status: 'running',
      started_at: '2026-06-27T12:00:00Z',
      finished_at: null,
      courses_found: 0,
      courses_new: 0,
      courses_removed: 0,
      courses_modified: 0,
      error_msg: null,
    }
    expect(run.finished_at).toBeNull()
  })

  it('accepts a failed scan with error_msg', () => {
    const run: ScanRun = {
      id: 3,
      school_registry_id: 2,
      status: 'error',
      started_at: '2026-06-27T14:00:00Z',
      finished_at: '2026-06-27T14:01:00Z',
      courses_found: 0,
      courses_new: 0,
      courses_removed: 0,
      courses_modified: 0,
      error_msg: 'Timeout lors du scrap',
    }
    expect(run.error_msg).toBe('Timeout lors du scrap')
  })
})

describe('ScanDiff type', () => {
  const sampleCourse: SchoolCourse = {
    id: 1,
    school_registry_id: 1,
    external_id: 'ext-1',
    title: 'Test Course',
    url: null,
    description: null,
    duration_hours: null,
    price: null,
    category: null,
    format: null,
    certification: null,
    first_seen_at: '2026-06-01T00:00:00Z',
    last_seen_at: '2026-06-27T00:00:00Z',
    last_updated_at: null,
    is_removed: false,
    removed_at: null,
  }

  it('accepts a diff with scan_run and all course arrays', () => {
    const diff: ScanDiff = {
      scan_run: {
        id: 1,
        status: 'completed',
        started_at: '2026-06-27T10:00:00Z',
        finished_at: '2026-06-27T10:05:00Z',
        courses_found: 10,
        courses_new: 3,
        courses_modified: 2,
        courses_removed: 1,
        error_msg: null,
      },
      new_courses: [sampleCourse],
      modified_courses: [],
      removed_courses: [],
    }
    expect(diff.new_courses).toHaveLength(1)
    expect(diff.modified_courses).toHaveLength(0)
  })

  it('accepts a null scan_run (no scans yet)', () => {
    const diff: ScanDiff = {
      scan_run: null,
      new_courses: [],
      modified_courses: [],
      removed_courses: [],
    }
    expect(diff.scan_run).toBeNull()
    expect(diff.new_courses).toEqual([])
  })
})

describe('DashboardCounts type (moved to Phase 1b section)', () => {
  it('accepts a valid counts object', () => {
    const counts: DashboardCounts = {
      total_schools: 5,
      unreviewed_scans: 2,
      closure_candidates: 3,
      creation_suggestions: 1,
    }
    expect(counts.total_schools).toBe(5)
  })

  it('dashboardApi.counts references DashboardCounts (compile-time check)', () => {
    expect(typeof dashboardApi.counts).toBe('function')
  })
})

describe('GapRecommendationList type (moved to Phase 1b section)', () => {
  it('accepts a closure recommendation', () => {
    const rec: GapRecommendationList = {
      id: 1,
      recommendation_type: 'closure',
      score: 85,
      status: 'draft',
      rationale: 'Fermeture recommandée',
      created_at: '2026-06-01T00:00:00Z',
    }
    expect(rec.recommendation_type).toBe('closure')
  })

  it('accepts a creation recommendation', () => {
    const rec: GapRecommendationList = {
      id: 2,
      recommendation_type: 'creation',
      score: 72,
      status: 'approved',
      rationale: null,
      created_at: '2026-06-15T00:00:00Z',
    }
    expect(rec.recommendation_type).toBe('creation')
  })

  it('gapApi.list references GapRecommendationList (compile-time check)', () => {
    expect(typeof gapApi.list).toBe('function')
  })
})
