/// <reference types="vitest/globals" />

/**
 * Tests de la page Archives (Phase 2.3).
 *
 * Couvre :
 *  - états chargement / erreur / vide
 *  - les deux sources sont bien filtrées (cours archivés, recommandations approuvées)
 *  - recherche locale sur les cours archivés
 *  - restauration : admin seulement, rechargement, échec affiché sans casser la page
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const mockCoursesList = vi.hoisted(() => vi.fn())
const mockCoursesRestore = vi.hoisted(() => vi.fn())
const mockGapList = vi.hoisted(() => vi.fn())
const mockUseAuth = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    coursesApi: { list: mockCoursesList, restore: mockCoursesRestore },
    gapApi: { list: mockGapList },
  }
})

vi.mock('@/lib/auth', () => ({ useAuth: () => mockUseAuth() }))

import { ApiError } from '@/lib/api'
import { ArchivesPage } from '../index'

const ARCHIVED_COURSE = {
  id: 7,
  title: 'Excel débutant',
  category: 'Bureautique',
  status: 'archived' as const,
  enrolled_count: 12,
  dropout_count: 3,
  popularity_score: 40,
  age_brackets: null,
  year: 2025,
  hours_estimated: 14,
  source: 'import',
  notes: null,
  created_at: '2025-01-10T10:00:00Z',
  updated_at: '2026-03-04T10:00:00Z',
}

const APPROVED_RECOMMENDATION = {
  id: 3,
  recommendation_type: 'closure' as const,
  score: 82,
  status: 'approved' as const,
  rationale: 'Aucune école ne propose plus ce contenu.',
  created_at: '2026-02-01T09:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  mockUseAuth.mockReturnValue({
    user: { id: 1, email: 'admin@test.com', role: 'admin' },
    isLoading: false,
  })
  mockCoursesList.mockResolvedValue([ARCHIVED_COURSE])
  mockGapList.mockResolvedValue([APPROVED_RECOMMENDATION])
  mockCoursesRestore.mockResolvedValue({ ...ARCHIVED_COURSE, status: 'active' })
})

describe('ArchivesPage — chargement', () => {
  it('affiche un indicateur pendant le chargement', () => {
    mockCoursesList.mockReturnValue(new Promise(() => {}))
    mockGapList.mockReturnValue(new Promise(() => {}))
    render(<ArchivesPage />)
    expect(screen.getByText('Chargement des archives...')).toBeInTheDocument()
  })

  it('affiche une erreur et permet de réessayer', async () => {
    mockCoursesList.mockRejectedValue(new ApiError(500, 'Erreur serveur.'))
    render(<ArchivesPage />)

    await waitFor(() => {
      expect(screen.getByText('Impossible de charger les archives')).toBeInTheDocument()
    })
    expect(screen.getByText('Erreur serveur.')).toBeInTheDocument()

    mockCoursesList.mockResolvedValue([ARCHIVED_COURSE])
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())
  })
})

describe('ArchivesPage — sources de données', () => {
  it('ne demande que les cours archivés et les recommandations approuvées', async () => {
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())

    expect(mockCoursesList).toHaveBeenCalledWith({ status: 'archived' })
    expect(mockGapList).toHaveBeenCalledWith({ status: 'approved', limit: 200 })
  })

  it('signale que la liste des recommandations est tronquée par le serveur', async () => {
    // Le serveur plafonne à 200 : afficher « (200) » sec ferait passer un
    // total tronqué pour le total réel.
    mockGapList.mockResolvedValue(
      Array.from({ length: 200 }, (_, i) => ({ ...APPROVED_RECOMMENDATION, id: i + 1 })),
    )
    render(<ArchivesPage />)

    await waitFor(() => expect(screen.getByText('(200 affichées)')).toBeInTheDocument())
    expect(
      screen.getByText(/Affichage limité aux 200 recommandations les mieux notées/),
    ).toBeInTheDocument()
  })

  it('n’affiche aucune mention de troncature en deçà du plafond', async () => {
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())

    expect(screen.queryByText(/Affichage limité/)).not.toBeInTheDocument()
  })

  it('affiche les deux sections avec leurs compteurs', async () => {
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())

    expect(screen.getByText('Bureautique')).toBeInTheDocument()
    expect(screen.getByText('Aucune école ne propose plus ce contenu.')).toBeInTheDocument()
    expect(screen.getByText('Fermeture')).toBeInTheDocument()
    expect(screen.getAllByText('(1)')).toHaveLength(2)
  })

  it('affiche des états vides distincts quand il n’y a rien', async () => {
    mockCoursesList.mockResolvedValue([])
    mockGapList.mockResolvedValue([])
    render(<ArchivesPage />)

    await waitFor(() => expect(screen.getByText('Aucun cours archivé')).toBeInTheDocument())
    expect(screen.getByText('Aucune recommandation validée')).toBeInTheDocument()
  })
})

describe('ArchivesPage — recherche', () => {
  it('filtre les cours archivés sur le titre', async () => {
    mockCoursesList.mockResolvedValue([
      ARCHIVED_COURSE,
      { ...ARCHIVED_COURSE, id: 8, title: 'Python avancé', category: 'Dév' },
    ])
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Python avancé')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Rechercher un cours archivé'), {
      target: { value: 'python' },
    })

    expect(screen.getByText('Python avancé')).toBeInTheDocument()
    expect(screen.queryByText('Excel débutant')).not.toBeInTheDocument()
  })
})

describe('ArchivesPage — volumétrie', () => {
  const manyCourses = Array.from({ length: 130 }, (_, i) => ({
    ...ARCHIVED_COURSE,
    id: i + 1,
    title: `Cours ${i + 1}`,
  }))

  it('ne rend que 100 lignes au départ puis déplie le reste à la demande', async () => {
    // CLAUDE.md : rendu progressif au-delà de 100 éléments (postes peu puissants).
    mockCoursesList.mockResolvedValue(manyCourses)
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Cours 1')).toBeInTheDocument())

    expect(screen.getByText('Cours 100')).toBeInTheDocument()
    expect(screen.queryByText('Cours 101')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Afficher les 30 cours restants' }))

    expect(screen.getByText('Cours 130')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /cours restants/ }),
    ).not.toBeInTheDocument()
  })

  it('ne propose pas de dépliage sous le seuil', async () => {
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())

    expect(screen.queryByRole('button', { name: /cours restants/ })).not.toBeInTheDocument()
  })
})

describe('ArchivesPage — restauration', () => {
  it('restaure un cours puis recharge la liste', async () => {
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())

    mockCoursesList.mockResolvedValue([])
    fireEvent.click(screen.getByRole('button', { name: /Restaurer/ }))

    await waitFor(() => expect(mockCoursesRestore).toHaveBeenCalledWith(7))
    await waitFor(() => expect(screen.getByText('Aucun cours archivé')).toBeInTheDocument())
  })

  it('ne recharge pas les recommandations, inchangées par une restauration', async () => {
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())
    expect(mockGapList).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: /Restaurer/ }))

    await waitFor(() => expect(mockCoursesList).toHaveBeenCalledTimes(2))
    expect(mockGapList).toHaveBeenCalledTimes(1)
  })

  it('affiche l’échec de restauration sans vider la page', async () => {
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())

    mockCoursesRestore.mockRejectedValue(new ApiError(403, 'Droits insuffisants.'))
    fireEvent.click(screen.getByRole('button', { name: /Restaurer/ }))

    await waitFor(() => {
      expect(
        screen.getByText('Restauration impossible : Droits insuffisants.'),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('Excel débutant')).toBeInTheDocument()
  })

  it('masque la colonne Actions pour un non-admin', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 2, email: 'user@test.com', role: 'user' },
      isLoading: false,
    })
    render(<ArchivesPage />)
    await waitFor(() => expect(screen.getByText('Excel débutant')).toBeInTheDocument())

    expect(screen.queryByRole('button', { name: /Restaurer/ })).not.toBeInTheDocument()
  })
})
