/// <reference types="vitest/globals" />

/**
 * Archivage par lot depuis Cours SCAP (Phase 2.4).
 *
 * `docs/SPEC.md` §5 : l'archivage massif est une action destructive —
 * confirmation obligatoire, et réservée aux admins.
 */

import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'

const mockGet = vi.hoisted(() => vi.fn())
const mockPost = vi.hoisted(() => vi.fn())
const mockArchiveBatch = vi.hoisted(() => vi.fn())
const mockUseAuth = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    api: { ...actual.api, get: mockGet, post: mockPost },
    coursesApi: { ...actual.coursesApi, archiveBatch: mockArchiveBatch },
  }
})

vi.mock('@/lib/auth', () => ({ useAuth: () => mockUseAuth() }))

import { ApiError } from '@/lib/api'
import { CoursesPage } from '../index'

function course(id: number, overrides: Record<string, unknown> = {}) {
  return {
    id,
    title: `Cours ${id}`,
    category: 'Bureautique',
    status: 'active' as const,
    enrolled_count: 10,
    dropout_count: 1,
    popularity_score: 50,
    age_brackets: null,
    year: 2026,
    hours_estimated: 14,
    source: 'scap',
    notes: null,
    created_at: '2026-01-01T10:00:00Z',
    updated_at: '2026-01-01T10:00:00Z',
    ...overrides,
  }
}

const COURSES = [course(1), course(2), course(3, { status: 'archived' })]

beforeEach(() => {
  vi.clearAllMocks()
  mockUseAuth.mockReturnValue({
    user: { id: 1, email: 'admin@test.com', role: 'admin' },
    isLoading: false,
  })
  mockGet.mockResolvedValue(COURSES)
  mockPost.mockResolvedValue({})
  mockArchiveBatch.mockResolvedValue({ archived: [1, 2], skipped: [], not_found: [] })
})

async function renderPage() {
  render(<CoursesPage />)
  await waitFor(() => expect(screen.getByText('Cours 1')).toBeInTheDocument())
}

describe('Sélection', () => {
  it('n’affiche aucune case pour un non-admin', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 2, email: 'user@test.com', role: 'user' },
      isLoading: false,
    })
    await renderPage()

    expect(screen.queryByLabelText(/Sélectionner/)).not.toBeInTheDocument()
  })

  it('interdit de sélectionner un cours déjà archivé', async () => {
    await renderPage()

    expect(screen.getByLabelText('Sélectionner « Cours 3 »')).toBeDisabled()
    expect(screen.getByLabelText('Sélectionner « Cours 1 »')).toBeEnabled()
  })

  it('« tout sélectionner » ne prend que les cours actifs affichés', async () => {
    await renderPage()

    fireEvent.click(screen.getByLabelText('Sélectionner tous les cours actifs affichés'))

    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText(/cours sélectionnés/)).toBeInTheDocument()
    expect(screen.getByLabelText('Sélectionner « Cours 3 »')).not.toBeChecked()
  })

  it('ne propose la barre d’action qu’une fois quelque chose de coché', async () => {
    await renderPage()

    expect(
      screen.queryByRole('button', { name: /Archiver la sélection/ }),
    ).not.toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Sélectionner « Cours 1 »'))

    expect(
      screen.getByRole('button', { name: /Archiver la sélection/ }),
    ).toBeInTheDocument()
  })

  it('la sélection ne suit que les lignes correspondant au filtre', async () => {
    await renderPage()
    fireEvent.click(screen.getByLabelText('Sélectionner « Cours 1 »'))
    fireEvent.click(screen.getByLabelText('Sélectionner « Cours 2 »'))

    fireEvent.change(screen.getByPlaceholderText('Rechercher par titre...'), {
      target: { value: 'Cours 1' },
    })

    // Cours 2 n'est plus affiché : il ne doit plus compter dans le lot.
    fireEvent.click(screen.getByRole('button', { name: /Archiver la sélection/ }))
    expect(
      screen.getByRole('button', { name: 'Archiver 1 cours' }),
    ).toBeInTheDocument()
  })
})

describe('Confirmation', () => {
  it('n’archive rien sans passer par le dialogue', async () => {
    await renderPage()
    fireEvent.click(screen.getByLabelText('Sélectionner « Cours 1 »'))

    fireEvent.click(screen.getByRole('button', { name: /Archiver la sélection/ }))

    expect(mockArchiveBatch).not.toHaveBeenCalled()
    expect(screen.getByText('Archiver la sélection ?')).toBeInTheDocument()
  })

  it('annonce le nombre exact avant d’agir', async () => {
    await renderPage()
    fireEvent.click(screen.getByLabelText('Sélectionner tous les cours actifs affichés'))
    fireEvent.click(screen.getByRole('button', { name: /Archiver la sélection/ }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText(/2 cours vont passer au statut/)).toBeInTheDocument()
    expect(
      within(dialog).getByRole('button', { name: 'Archiver 2 cours' }),
    ).toBeInTheDocument()
  })

  it('envoie les identifiants sélectionnés après confirmation', async () => {
    await renderPage()
    fireEvent.click(screen.getByLabelText('Sélectionner tous les cours actifs affichés'))
    fireEvent.click(screen.getByRole('button', { name: /Archiver la sélection/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Archiver 2 cours' }))

    await waitFor(() => expect(mockArchiveBatch).toHaveBeenCalledWith([1, 2]))
  })
})

describe('Retour du serveur', () => {
  it('résume ce qui a été fait, y compris les cas partiels', async () => {
    mockArchiveBatch.mockResolvedValue({
      archived: [1],
      skipped: [2],
      not_found: [99],
    })
    await renderPage()
    fireEvent.click(screen.getByLabelText('Sélectionner tous les cours actifs affichés'))
    fireEvent.click(screen.getByRole('button', { name: /Archiver la sélection/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Archiver 2 cours' }))

    await waitFor(() =>
      expect(
        screen.getByText('1 cours archivé(s) · 1 déjà archivé(s) · 1 introuvable(s)'),
      ).toBeInTheDocument(),
    )
  })

  it('affiche l’échec et garde la sélection', async () => {
    mockArchiveBatch.mockRejectedValue(new ApiError(403, 'Accès réservé aux administrateurs.'))
    await renderPage()
    fireEvent.click(screen.getByLabelText('Sélectionner « Cours 1 »'))
    fireEvent.click(screen.getByRole('button', { name: /Archiver la sélection/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Archiver 1 cours' }))

    await waitFor(() =>
      expect(
        screen.getByText('Archivage impossible : Accès réservé aux administrateurs.'),
      ).toBeInTheDocument(),
    )
    expect(screen.getByLabelText('Sélectionner « Cours 1 »')).toBeChecked()
  })

  it('vide la sélection après un archivage réussi', async () => {
    await renderPage()
    fireEvent.click(screen.getByLabelText('Sélectionner tous les cours actifs affichés'))
    fireEvent.click(screen.getByRole('button', { name: /Archiver la sélection/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Archiver 2 cours' }))

    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: /Archiver la sélection/ }),
      ).not.toBeInTheDocument(),
    )
  })
})
