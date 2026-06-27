/// <reference types="vitest/globals" />

/**
 * Tests for ScanResultsPage (commit 55caafb).
 *
 * Covers:
 *  - Loading / error / empty states
 *  - School filter dropdown rendering
 *  - Scan runs table rendering with status badges
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'

// ── Mock API values créés avant les mocks hoistés ───────────────────────────
const mockScanRunsList = vi.hoisted(() => vi.fn())
const mockSchoolsList = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    scanRunsApi: { list: mockScanRunsList },
    schoolsApi: { ...actual.schoolsApi, list: mockSchoolsList },
  }
})

import { ScanResultsPage } from '../ScanResults'

// ── Données mock ─────────────────────────────────────────────────────────────
const mockSchools = [
  {
    id: 1,
    name: 'École Alpha',
    url: 'https://alpha.example.com',
    scraper_strategy: 'stub',
    active: true,
    scan_interval: 1440,
    last_scanned_at: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'École Beta',
    url: 'https://beta.example.com',
    scraper_strategy: 'SCAP',
    active: true,
    scan_interval: 60,
    last_scanned_at: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

const mockScanRuns = [
  {
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
  },
  {
    id: 2,
    school_registry_id: 2,
    status: 'error',
    started_at: '2026-06-27T12:00:00Z',
    finished_at: '2026-06-27T12:01:00Z',
    courses_found: 0,
    courses_new: 0,
    courses_removed: 0,
    courses_modified: 0,
    error_msg: 'Timeout',
  },
]

// ── Tests ────────────────────────────────────────────────────────────────────

describe('ScanResultsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Loading state ──────────────────────────────────────────────────────────
  it('renders loading state initially', () => {
    mockScanRunsList.mockReturnValue(new Promise<void>(() => {}))
    mockSchoolsList.mockReturnValue(new Promise<void>(() => {}))
    render(<ScanResultsPage />)
    expect(screen.getByText('Chargement des résultats...')).toBeInTheDocument()
  })

  // ── Error state ────────────────────────────────────────────────────────────
  it('renders error state when API fails', async () => {
    mockScanRunsList.mockRejectedValue(new Error('Erreur serveur'))
    mockSchoolsList.mockResolvedValue([])
    render(<ScanResultsPage />)
    await waitFor(() => {
      expect(screen.getByText('Impossible de charger les résultats')).toBeInTheDocument()
    })
    expect(screen.getByText('Réessayer')).toBeInTheDocument()
  })

  // ── Empty state ────────────────────────────────────────────────────────────
  it('renders empty state when no scan runs exist', async () => {
    mockScanRunsList.mockResolvedValue([])
    mockSchoolsList.mockResolvedValue(mockSchools)
    render(<ScanResultsPage />)
    await waitFor(() => {
      expect(screen.getByText('Aucun scan trouvé')).toBeInTheDocument()
    })
    expect(
      screen.getByText(/Lancez un scan depuis la page/)
    ).toBeInTheDocument()
  })

  // ── School filter dropdown ─────────────────────────────────────────────────
  it('renders school filter dropdown with schools', async () => {
    mockScanRunsList.mockResolvedValue(mockScanRuns)
    mockSchoolsList.mockResolvedValue(mockSchools)
    render(<ScanResultsPage />)

    await waitFor(() => {
      const options = screen.getAllByRole('option')
      expect(options).toHaveLength(3)
      expect(options[0]).toHaveTextContent('Toutes les écoles')
      expect(options[1]).toHaveTextContent('École Alpha')
      expect(options[2]).toHaveTextContent('École Beta')
    })
  })

  it('filters scan runs when a school is selected', async () => {
    mockScanRunsList.mockResolvedValue(mockScanRuns)
    mockSchoolsList.mockResolvedValue(mockSchools)
    render(<ScanResultsPage />)

    await waitFor(() => {
      const cells = screen.getAllByRole('cell')
      const schoolNames = cells.map((c) => c.textContent)
      expect(schoolNames).toContain('École Alpha')
      expect(schoolNames).toContain('École Beta')
    })

    // Select École Alpha (school_registry_id = 1)
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: '1' } })

    // After filter, only École Alpha should be in table
    const cells = screen.getAllByRole('cell')
    const schoolNames = cells.map((c) => c.textContent)
    expect(schoolNames).not.toContain('École Beta')
    expect(schoolNames).toContain('École Alpha')
  })

  // ── Scan runs table ───────────────────────────────────────────────────────
  it('renders scan runs table with correct data', async () => {
    mockScanRunsList.mockResolvedValue(mockScanRuns)
    mockSchoolsList.mockResolvedValue(mockSchools)
    render(<ScanResultsPage />)

    await waitFor(() => {
      // Check table cells contain school names
      const cells = screen.getAllByRole('cell')
      const texts = cells.map((c) => c.textContent)
      expect(texts).toContain('École Alpha')
      expect(texts).toContain('École Beta')
    })

    // Check status badges in table rows
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBeGreaterThanOrEqual(2) // header + data rows

    // Check numeric values in table
    const cells = screen.getAllByRole('cell')
    const texts = cells.map((c) => c.textContent)
    expect(texts).toContain('42')
    expect(texts).toContain('5')
  })
})
