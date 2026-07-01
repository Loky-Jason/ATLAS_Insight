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
const mockTestConnection = vi.hoisted(() => vi.fn().mockResolvedValue({ success: true }))
const mockListStrategies = vi.hoisted(() => vi.fn().mockResolvedValue([]))

// L'ApiError du module réel est conservé via importActual
vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    schoolsApi: {
      list: mockList,
      listStrategies: mockListStrategies,
      create: mockCreate,
      update: mockUpdate,
      delete: mockDelete,
      scan: mockScan,
      diff: mockDiff,
      testConnection: mockTestConnection,
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

  // ── Error banner shows and scan message can be dismissed ───────────────────
  it('shows error banner on scan API failure and dismisses scan message', async () => {
    mockList.mockResolvedValue(mockSchools)
    mockScan.mockRejectedValue(new ApiError(500, 'Scan failed'))

    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('École A')).toBeInTheDocument()
    })

    // Click scan button
    const scanButtons = screen.getAllByTitle('Lancer un scan')
    fireEvent.click(scanButtons[0]!)

    // Wait for error banner (scanMsg area + errorMsg fallback both show the text)
    await waitFor(() => {
      expect(screen.getByText('Scan failed')).toBeInTheDocument()
    })

    // Dismiss scan message — errorMsg fallback card remains visible
    const closeButtons = screen.getAllByText('Fermer')
    fireEvent.click(closeButtons[0]!)

    // scanMsg card is gone, but errorMsg card still shows "Scan failed"
    await waitFor(() => {
      // Only one "Scan failed" text visible now (from errorMsg, not scanMsg)
      const items = screen.getAllByText('Scan failed')
      expect(items.length).toBe(1)
    })
  })

  // ── Scan error_msg from status: 'error' response ──────────────────────────
  it('shows error feedback when scan returns status "error"', async () => {
    mockList.mockResolvedValue(mockSchools)
    mockScan.mockResolvedValue({
      school_name: 'École A',
      status: 'error',
      found: 0,
      new: 0,
      modified: 0,
      removed: 0,
      scan_run_id: 42,
      error_msg: 'La connexion au site a échoué',
    })

    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('École A')).toBeInTheDocument()
    })

    // Click scan button
    const scanButtons = screen.getAllByTitle('Lancer un scan')
    fireEvent.click(scanButtons[0]!)

    // Wait for error message from scan response
    await waitFor(() => {
      expect(
        screen.getByText('La connexion au site a échoué')
      ).toBeInTheDocument()
    })

    // The scanMsg card should have destructive styling (red border)
    const scanCard = screen.getByText('La connexion au site a échoué').closest('.border-destructive\\/50')
    expect(scanCard).not.toBeNull()

    // Verify it's in scan message area, not errorMsg area
    expect(screen.queryByText('Échec du scan')).toBeNull()
  })

  it('shows fallback error text when error_msg is null', async () => {
    mockList.mockResolvedValue(mockSchools)
    mockScan.mockResolvedValue({
      school_name: 'École A',
      status: 'error',
      found: 0,
      new: 0,
      modified: 0,
      removed: 0,
      scan_run_id: 43,
      error_msg: null,
    })

    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('École A')).toBeInTheDocument()
    })

    const scanButtons = screen.getAllByTitle('Lancer un scan')
    fireEvent.click(scanButtons[0]!)

    await waitFor(() => {
      expect(
        screen.getByText('Échec du scan')
      ).toBeInTheDocument()
    })
  })
})

// ── SchoolFormDialog tests ───────────────────────────────────────────────────
describe('SchoolFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockTestConnection.mockResolvedValue({ success: true })
  })

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

  it('shows error in dialog when test-connection fails and keeps dialog open', async () => {
    mockTestConnection.mockResolvedValueOnce({ success: false, error_msg: 'Erreur HTTP 503.' })
    mockList.mockResolvedValue([])
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('Aucune école configurée')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Ajouter une école'))
    fireEvent.change(screen.getByLabelText('Nom'), { target: { value: 'Site KO' } })
    fireEvent.change(screen.getByLabelText('URL'), { target: { value: 'https://ko.example.com' } })
    fireEvent.click(screen.getByText('Ajouter'))

    await waitFor(() => {
      expect(screen.getByText('Erreur HTTP 503.')).toBeInTheDocument()
    })

    // Dialog toujours ouvert (le bouton submit est visible), onSave jamais appelé
    expect(screen.getByRole('button', { name: /Ajouter$/i })).toBeInTheDocument()
    expect(mockCreate).not.toHaveBeenCalled()
  })

  it('shows error in dialog when testConnection throws ApiError', async () => {
    mockTestConnection.mockRejectedValue(new ApiError(0, 'Le serveur est inaccessible.'))
    mockList.mockResolvedValue([])
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('Aucune école configurée')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Ajouter une école'))
    fireEvent.change(screen.getByLabelText('Nom'), { target: { value: 'Site KO' } })
    fireEvent.change(screen.getByLabelText('URL'), { target: { value: 'https://ko.example.com' } })
    fireEvent.click(screen.getByText('Ajouter'))

    await waitFor(() => {
      expect(screen.getByText('Le serveur est inaccessible.')).toBeInTheDocument()
    })

    // Dialog stays open, onSave never called
    expect(screen.getByRole('button', { name: /Ajouter$/i })).toBeInTheDocument()
    expect(mockCreate).not.toHaveBeenCalled()
  })

  it('shows fallback error message when error_msg is empty', async () => {
    mockTestConnection.mockResolvedValueOnce({ success: false }) // no error_msg
    mockList.mockResolvedValue([])
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('Aucune école configurée')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Ajouter une école'))
    fireEvent.change(screen.getByLabelText('Nom'), { target: { value: 'Site KO' } })
    fireEvent.change(screen.getByLabelText('URL'), { target: { value: 'https://ko.example.com' } })
    fireEvent.click(screen.getByText('Ajouter'))

    await waitFor(() => {
      expect(screen.getByText('Connexion échouée.')).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: /Ajouter$/i })).toBeInTheDocument()
    expect(mockCreate).not.toHaveBeenCalled()
  })

  it('calls onSave and closes dialog when test-connection succeeds', async () => {
    mockTestConnection.mockResolvedValue({ success: true })
    mockCreate.mockResolvedValue(mockSchools[0]!)
    mockList.mockResolvedValue([])
    render(<SchoolsPage />)

    await waitFor(() => {
      expect(screen.getByText('Aucune école configurée')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Ajouter une école'))
    fireEvent.change(screen.getByLabelText('Nom'), { target: { value: 'Nouvelle École' } })
    fireEvent.change(screen.getByLabelText('URL'), { target: { value: 'https://nouvelle.example.com' } })
    fireEvent.click(screen.getByText('Ajouter'))

    // testConnection called with the right URL
    await waitFor(() => {
      expect(mockTestConnection).toHaveBeenCalledWith('https://nouvelle.example.com')
    })
    // Then onSave is called (create)
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled()
    })
    // Dialog closes
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })
})
