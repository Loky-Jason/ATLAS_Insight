/// <reference types="vitest/globals" />

/**
 * Tests for SchoolsPage and SchoolFormDialog (commits 55caafb + 68850d7).
 *
 * Covers:
 *  - Loading / error / empty states
 *  - Schools table rendering
 *  - SchoolFormDialog form initialisation (create vs edit mode)
 *  - Error banner dismiss
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'

// ── Mock API values créés avant les mocks hoistés ───────────────────────────
const mockList = vi.hoisted(() => vi.fn())
const mockCreate = vi.hoisted(() => vi.fn())
const mockUpdate = vi.hoisted(() => vi.fn())
const mockDelete = vi.hoisted(() => vi.fn())
const mockScan = vi.hoisted(() => vi.fn())
const mockDiff = vi.hoisted(() => vi.fn())

// L'ApiError du module réel est conservé via importActual
vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    schoolsApi: {
      list: mockList,
      create: mockCreate,
      update: mockUpdate,
      delete: mockDelete,
      scan: mockScan,
      diff: mockDiff,
    },
  }
})

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'admin@test.com', role: 'admin' },
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

import { ApiError } from '@/lib/api'
import { SchoolsPage } from '../Schools'

// ── Données mock ─────────────────────────────────────────────────────────────
const mockSchools = [
  {
    id: 1,
    name: 'École A',
    url: 'https://ecole-a.example.com',
    scraper_strategy: 'stub',
    active: true,
    scan_interval: 1440,
    last_scanned_at: null,
    created_at: '2026-06-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'École B',
    url: 'https://ecole-b.example.com',
    scraper_strategy: 'SCAP',
    active: false,
    scan_interval: 60,
    last_scanned_at: '2026-06-27T12:00:00Z',
    created_at: '2026-06-01T00:00:00Z',
  },
]

// ── Tests ────────────────────────────────────────────────────────────────────

describe('SchoolsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Loading state ──────────────────────────────────────────────────────────
  it('renders loading state initially', () => {
    mockList.mockReturnValue(new Promise<void>(() => {}))
    render(<SchoolsPage />)
    expect(screen.getByText('Chargement des écoles...')).toBeInTheDocument()
  })

  // ── Error state ────────────────────────────────────────────────────────────
  it('renders error state when API fails', async () => {
    mockList.mockRejectedValue(new ApiError(500, 'Erreur réseau'))
    render(<SchoolsPage />)
    await waitFor(() => {
      expect(screen.getByText('Impossible de charger les écoles')).toBeInTheDocument()
    })
    expect(screen.getByText('Erreur réseau')).toBeInTheDocument()
    expect(screen.getByText('Réessayer')).toBeInTheDocument()
  })

  // ── Empty state ────────────────────────────────────────────────────────────
  it('renders empty state when no schools exist', async () => {
    mockList.mockResolvedValue([])
    render(<SchoolsPage />)
    await waitFor(() => {
      expect(screen.getByText('Aucune école configurée')).toBeInTheDocument()
    })
    expect(
      screen.getByText(/Ajoutez une première école/)
    ).toBeInTheDocument()
  })

  // ── Schools table ──────────────────────────────────────────────────────────
  it('renders schools in a table when data loads', async () => {
    mockList.mockResolvedValue(mockSchools)
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('École A')).toBeInTheDocument()
    })
    expect(screen.getByText('École B')).toBeInTheDocument()
  })

  // ── Search filters schools ─────────────────────────────────────────────────
  it('filters schools by name via search input', async () => {
    mockList.mockResolvedValue(mockSchools)
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('École A')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText('Rechercher par nom...')
    fireEvent.change(searchInput, { target: { value: 'B' } })

    expect(screen.queryByText('École A')).not.toBeInTheDocument()
    expect(screen.getByText('École B')).toBeInTheDocument()
  })

  // ── Error banner shows and can be dismissed ────────────────────────────────
  it('shows and dismisses error banner on scan failure', async () => {
    mockList.mockResolvedValue(mockSchools)
    mockScan.mockRejectedValue(new ApiError(500, 'Scan failed'))

    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('École A')).toBeInTheDocument()
    })

    // Click scan button
    const scanButtons = screen.getAllByTitle('Lancer un scan')
    fireEvent.click(scanButtons[0]!)

    // Wait for error banner
    await waitFor(() => {
      expect(screen.getByText('Scan failed')).toBeInTheDocument()
    })

    // Dismiss error banner
    fireEvent.click(screen.getByText('Fermer'))
    await waitFor(() => {
      expect(screen.queryByText('Scan failed')).not.toBeInTheDocument()
    })
  })
})

// ── SchoolFormDialog tests ───────────────────────────────────────────────────
describe('SchoolFormDialog', () => {
  it('opens create dialog when "Ajouter une école" is clicked', async () => {
    mockList.mockResolvedValue([])
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('Aucune école configurée')).toBeInTheDocument()
    })

    const addButton = screen.getByText('Ajouter une école')
    fireEvent.click(addButton)

    // Dialog opens — check by role and form field
    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(screen.getByLabelText('Nom')).toHaveValue('')
    expect(screen.getByLabelText('URL')).toHaveValue('')
  })

  it('opens edit dialog with pre-filled form', async () => {
    mockList.mockResolvedValue(mockSchools)
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('École A')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByTitle('Modifier')
    fireEvent.click(editButtons[0]!)

    expect(screen.getByText(/Modifier l'école/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Nom')).toHaveValue('École A')
    expect(screen.getByLabelText('URL')).toHaveValue('https://ecole-a.example.com')
  })

  it('calls onSave with form data when submitted in create mode', async () => {
    mockList.mockResolvedValue([])
    mockCreate.mockResolvedValue(mockSchools[0]!)
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('Aucune école configurée')).toBeInTheDocument()
    })

    // Open create dialog
    fireEvent.click(screen.getByText('Ajouter une école'))

    // Fill form
    fireEvent.change(screen.getByLabelText('Nom'), { target: { value: 'Nouvelle École' } })
    fireEvent.change(screen.getByLabelText('URL'), { target: { value: 'https://nouvelle.example.com' } })

    // Submit
    fireEvent.click(screen.getByText('Ajouter'))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Nouvelle École',
          url: 'https://nouvelle.example.com',
        })
      )
    })
  })
})
