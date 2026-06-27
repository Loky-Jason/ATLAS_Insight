/// <reference types="vitest/globals" />

/**
 * Tests for ChangeLogPage (commit 55caafb).
 *
 * Covers:
 *  - Loading / error / empty states
 *  - Timeline grouping logic (school with diffs sorted by date)
 *  - Conditional rendering of new / modified / removed sections
 *  - "5+ autres" overflow indicator
 */

import { render, screen, waitFor } from '@testing-library/react'

// ── Mock API values créés avant les mocks hoistés ───────────────────────────
const mockList = vi.hoisted(() => vi.fn())
const mockDiff = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    schoolsApi: {
      ...actual.schoolsApi,
      list: mockList,
      diff: mockDiff,
    },
  }
})

import { ChangeLogPage } from '../ChangeLog'

// ── Helpers ──────────────────────────────────────────────────────────────────
function makeSchool(id: number, name: string) {
  return {
    id,
    name,
    url: `https://${name.toLowerCase()}.example.com`,
    scraper_strategy: 'stub' as const,
    active: true,
    scan_interval: 1440,
    last_scanned_at: null,
    created_at: '2026-01-01T00:00:00Z',
  }
}

function makeCourse(id: number, title: string) {
  return {
    id,
    school_registry_id: 1,
    external_id: `ext-${id}`,
    title,
    url: null,
    description: null,
    duration_hours: null,
    price: null,
    category: null,
    format: null,
    certification: null,
    first_seen_at: '2026-06-27T00:00:00Z',
    last_seen_at: '2026-06-27T00:00:00Z',
    last_updated_at: null,
    is_removed: false,
    removed_at: null,
  }
}

function makeDiff(newCourses: number, modified: number, removed: number, startedAt: string) {
  return {
    scan_run: {
      id: 1,
      status: 'completed' as const,
      started_at: startedAt,
      finished_at: startedAt,
      courses_found: newCourses + modified + removed,
      courses_new: newCourses,
      courses_modified: modified,
      courses_removed: removed,
      error_msg: null,
    },
    new_courses: Array.from({ length: newCourses }, (_, i) =>
      makeCourse(i + 100, `Nouveau cours ${i + 1}`)
    ),
    modified_courses: Array.from({ length: modified }, (_, i) =>
      makeCourse(i + 200, `Cours modifié ${i + 1}`)
    ),
    removed_courses: Array.from({ length: removed }, (_, i) =>
      makeCourse(i + 300, `Cours supprimé ${i + 1}`)
    ),
  }
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('ChangeLogPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Loading state ──────────────────────────────────────────────────────────
  it('renders loading state initially', () => {
    mockList.mockReturnValue(new Promise<void>(() => {}))
    render(<ChangeLogPage />)
    expect(screen.getByText('Chargement...')).toBeInTheDocument()
  })

  // ── Error state ────────────────────────────────────────────────────────────
  it('renders error state when schools API fails', async () => {
    mockList.mockRejectedValue(new Error('Erreur API'))
    render(<ChangeLogPage />)
    await waitFor(() =>
      expect(
        screen.getByText('Impossible de charger les modifications')
      ).toBeInTheDocument()
    )
    expect(screen.getByText('Réessayer')).toBeInTheDocument()
  })

  // ── Empty state ────────────────────────────────────────────────────────────
  it('renders empty state when no diffs have changes', async () => {
    mockList.mockResolvedValue([makeSchool(1, 'École Vide')])
    mockDiff.mockResolvedValue({
      scan_run: null,
      new_courses: [],
      modified_courses: [],
      removed_courses: [],
    })

    render(<ChangeLogPage />)
    await waitFor(() =>
      expect(
        screen.getByText('Aucun changement détecté')
      ).toBeInTheDocument()
    )
  })

  // ── Timeline: single school with changes ───────────────────────────────────
  it('renders a timeline entry for a school with changes', async () => {
    mockList.mockResolvedValue([makeSchool(1, 'École Active')])
    mockDiff.mockResolvedValue(makeDiff(2, 1, 1, '2026-06-27T10:00:00Z'))

    render(<ChangeLogPage />)

    await waitFor(() => {
      expect(screen.getByText('École Active')).toBeInTheDocument()
    })

    // Check that sections render
    expect(screen.getByText(/2 nouveaux?/)).toBeInTheDocument()
    expect(screen.getByText(/1 modifiés?/)).toBeInTheDocument()
    expect(screen.getByText(/1 supprimés?/)).toBeInTheDocument()

    // Check course names
    expect(screen.getByText('Nouveau cours 1')).toBeInTheDocument()
    expect(screen.getByText('Cours modifié 1')).toBeInTheDocument()
    expect(screen.getByText('Cours supprimé 1')).toBeInTheDocument()

    // Check total changes indicator
    expect(screen.getByText('4 changements')).toBeInTheDocument()
  })

  // ── Timeline: multiple schools sorted by date ──────────────────────────────
  it('sorts schools by scan date descending', async () => {
    const schoolA = makeSchool(1, 'École A')
    const schoolB = makeSchool(2, 'École B')

    mockList.mockResolvedValue([schoolA, schoolB])

    mockDiff.mockImplementation(async (id: number) => {
      if (id === 1) return makeDiff(1, 0, 0, '2026-06-01T00:00:00Z')
      if (id === 2) return makeDiff(1, 0, 0, '2026-06-27T00:00:00Z')
      return makeDiff(0, 0, 0, '')
    })

    render(<ChangeLogPage />)

    await waitFor(() => {
      const cards = screen.getAllByText(/École [AB]/)
      expect(cards[0]).toHaveTextContent('École B')
      expect(cards[1]).toHaveTextContent('École A')
    })
  })

  // ── Timeline: > 5 courses shows "+N autres" ────────────────────────────────
  it('shows "+N autres" when more than 5 courses in a section', async () => {
    mockList.mockResolvedValue([makeSchool(1, 'Big School')])
    mockDiff.mockResolvedValue(makeDiff(7, 0, 0, '2026-06-27T10:00:00Z'))

    render(<ChangeLogPage />)

    await waitFor(() => {
      expect(screen.getByText(/7 nouveaux?/)).toBeInTheDocument()
    })

    expect(screen.getByText('+2 autres')).toBeInTheDocument()
  })

  // ── Timeline: school without scan_run is excluded ──────────────────────────
  it('excludes schools with null scan_run from timeline', async () => {
    mockList.mockResolvedValue([
      makeSchool(1, 'With Scan'),
      makeSchool(2, 'No Scan'),
    ])

    mockDiff.mockImplementation(async (id: number) => {
      if (id === 1) return makeDiff(1, 0, 0, '2026-06-27T10:00:00Z')
      return { scan_run: null, new_courses: [], modified_courses: [], removed_courses: [] }
    })

    render(<ChangeLogPage />)

    await waitFor(() => {
      expect(screen.getByText('With Scan')).toBeInTheDocument()
    })

    expect(screen.queryByText('No Scan')).not.toBeInTheDocument()
  })

  // ── Single change uses singular "changement" ───────────────────────────────
  it('uses singular for exactly 1 change', async () => {
    mockList.mockResolvedValue([makeSchool(1, 'Single')])
    mockDiff.mockResolvedValue(makeDiff(1, 0, 0, '2026-06-27T10:00:00Z'))

    render(<ChangeLogPage />)

    await waitFor(() => {
      expect(screen.getByText('1 changement')).toBeInTheDocument()
    })
  })
})
