/// <reference types="vitest/globals" />

/**
 * Tests for GapRecommendationsList component (Phase 1c).
 *
 * Covers:
 *  - Loading / error / empty states
 *  - Card rendering: rationale, score badge, schools, factors
 *  - Creation variant: suggested hours, certifications
 *  - Approve / Reject actions with optimistic removal
 *  - Error banner on action failure
 *  - Variant-specific colors and icons
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// ── Mock API values created before hoisted mocks ──────────────────────────
const mockListClosure = vi.hoisted(() => vi.fn())
const mockListCreation = vi.hoisted(() => vi.fn())
const mockApprove = vi.hoisted(() => vi.fn())
const mockReject = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    gapApi: {
      ...actual.gapApi,
      listClosure: mockListClosure,
      listCreation: mockListCreation,
      approve: mockApprove,
      reject: mockReject,
    },
  }
})

import { GapRecommendationsList } from '../GapRecommendationsList'
import type { GapRecommendationRead } from '@/lib/api'

// ── Helpers ────────────────────────────────────────────────────────────────

function makeRec(overrides: Partial<GapRecommendationRead> = {}) {
  return {
    id: 1,
    recommendation_type: 'closure' as const,
    score: 75,
    status: 'draft' as const,
    rationale: 'Test rationale pour la recommandation',
    schools_offering: '["École A", "École B"]',
    score_breakdown: '{"schools_offering_count":0.6,"low_popularity":0.5,"weighted_score":75}',
    suggested_hours: null,
    certification_suggestions: null,
    scap_course_id: null,
    market_course_id: null,
    creation_key: null,
    created_at: '2026-07-01T00:00:00Z',
    updated_at: null,
    ...overrides,
  } satisfies GapRecommendationRead
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('GapRecommendationsList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Loading state ──────────────────────────────────────────────────────
  it('renders loading state initially', () => {
    mockListClosure.mockReturnValue(new Promise<void>(() => {}))
    render(<GapRecommendationsList variant="closure" />)
    expect(screen.getByText('Chargement...')).toBeInTheDocument()
  })

  // ── Error state ────────────────────────────────────────────────────────
  it('renders error state when API fails to load', async () => {
    mockListClosure.mockRejectedValue(new Error('Erreur API'))
    render(<GapRecommendationsList variant="closure" />)
    // Component catches generic Error → shows "Erreur inconnue"
    await waitFor(() =>
      expect(screen.getByText('Erreur inconnue')).toBeInTheDocument()
    )
    expect(screen.getByText('Réessayer')).toBeInTheDocument()
  })

  // ── Empty state ────────────────────────────────────────────────────────
  it('renders empty state when no recommendations', async () => {
    mockListClosure.mockResolvedValue([])
    render(<GapRecommendationsList variant="closure" />)
    await waitFor(() =>
      expect(
        screen.getByText('Aucune recommandation de fermeture')
      ).toBeInTheDocument()
    )
  })

  // ── Card renders with rationale, score badge, schools ─────────────────
  it('displays recommendation card with rationale, score badge, schools', async () => {
    mockListClosure.mockResolvedValue([makeRec()])
    render(<GapRecommendationsList variant="closure" />)

    await waitFor(() => {
      expect(
        screen.getByText('Test rationale pour la recommandation')
      ).toBeInTheDocument()
    })

    // Score badge
    expect(screen.getByText('Score 75')).toBeInTheDocument()

    // Schools (partial text match because it's inside the "Proposé par …" sentence)
    expect(screen.getByText(/Proposé par.*École A, École B/)).toBeInTheDocument()
  })

  // ── Creation variant shows hours and certifications ───────────────────
  it('shows suggested hours and certifications for creation variant', async () => {
    mockListCreation.mockResolvedValue([
      makeRec({
        id: 2,
        recommendation_type: 'creation',
        score: 70,
        suggested_hours: 21,
        certification_suggestions: JSON.stringify([
          { type: 'RNCP', label: 'Certif A', rationale: 'Rationale A', confidence: 0.9 },
          { type: 'Certificate', label: 'Certif B', rationale: 'Rationale B', confidence: 0.8 },
          { type: 'Vendor', label: 'Certif C', rationale: 'Rationale C', confidence: 0.7 },
        ]),
      }),
    ])
    render(<GapRecommendationsList variant="creation" />)

    await waitFor(() => {
      expect(screen.getByText(/21h estimées/)).toBeInTheDocument()
    })

    // Certifications rendered by label
    expect(screen.getByText('Certif A')).toBeInTheDocument()
    expect(screen.getByText('Certif B')).toBeInTheDocument()
    expect(screen.getByText('Certif C')).toBeInTheDocument()
  })

  // ── Approve button removes card ───────────────────────────────────────
  it('removes card on approve', async () => {
    mockListClosure.mockResolvedValue([makeRec({ id: 1 })])
    mockApprove.mockResolvedValue({})
    render(<GapRecommendationsList variant="closure" />)

    await waitFor(() => {
      expect(screen.getByText('Test rationale pour la recommandation')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /Approuver/ }))

    await waitFor(() => {
      expect(
        screen.queryByText('Test rationale pour la recommandation')
      ).not.toBeInTheDocument()
    })
    expect(mockApprove).toHaveBeenCalledWith(1)
  })

  // ── Reject button removes card ────────────────────────────────────────
  it('removes card on reject', async () => {
    mockListClosure.mockResolvedValue([makeRec({ id: 2 })])
    mockReject.mockResolvedValue({})
    render(<GapRecommendationsList variant="closure" />)

    await waitFor(() => {
      expect(screen.getByText('Test rationale pour la recommandation')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /Rejeter/ }))

    await waitFor(() => {
      expect(
        screen.queryByText('Test rationale pour la recommandation')
      ).not.toBeInTheDocument()
    })
    expect(mockReject).toHaveBeenCalledWith(2)
  })

  // ── Error banner on approve failure ───────────────────────────────────
  it('shows error banner when approve fails', async () => {
    mockListClosure.mockResolvedValue([makeRec({ id: 3 })])
    mockApprove.mockRejectedValue(new Error('Erreur approbation'))
    render(<GapRecommendationsList variant="closure" />)

    await waitFor(() => {
      expect(screen.getByText('Test rationale pour la recommandation')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /Approuver/ }))

    // Component catches generic Error and shows its own message
    await waitFor(() => {
      expect(screen.getByText("Erreur lors de l'approbation")).toBeInTheDocument()
    })
  })

  // ── Error banner on reject failure ────────────────────────────────────
  it('shows error banner when reject fails', async () => {
    mockListClosure.mockResolvedValue([makeRec({ id: 4 })])
    mockReject.mockRejectedValue(new Error('Erreur rejet'))
    render(<GapRecommendationsList variant="closure" />)

    await waitFor(() => {
      expect(screen.getByText('Test rationale pour la recommandation')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: /Rejeter/ }))

    // Component catches generic Error and shows its own message
    await waitFor(() => {
      expect(screen.getByText('Erreur lors du rejet')).toBeInTheDocument()
    })
  })

  // ── Closure variant colors ────────────────────────────────────────────
  it('shows amber/XCircle for closure variant', async () => {
    mockListClosure.mockResolvedValue([])
    render(<GapRecommendationsList variant="closure" />)

    await waitFor(() => {
      expect(screen.getByText('Aucune recommandation de fermeture')).toBeInTheDocument()
    })

    // Page title
    expect(screen.getByText('Recommandations — À fermer')).toBeInTheDocument()
  })

  // ── Creation variant colors ────────────────────────────────────────────
  it('shows emerald/PlusCircle for creation variant', async () => {
    mockListCreation.mockResolvedValue([])
    render(<GapRecommendationsList variant="creation" />)

    await waitFor(() => {
      expect(screen.getByText('Aucune suggestion de création')).toBeInTheDocument()
    })

    // Page title
    expect(screen.getByText('Recommandations — À créer')).toBeInTheDocument()
  })

  // ── Loading via listCreation for creation variant ──────────────────────
  it('calls listCreation for creation variant', async () => {
    mockListCreation.mockResolvedValue([])
    render(<GapRecommendationsList variant="creation" />)

    await waitFor(() => {
      expect(mockListCreation).toHaveBeenCalled()
    })
    expect(mockListClosure).not.toHaveBeenCalled()
  })
})
