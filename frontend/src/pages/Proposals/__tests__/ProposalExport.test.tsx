/// <reference types="vitest/globals" />

/**
 * Export PDF d'une proposition (Phase 2.1) — bouton de la page Propositions
 * et helper `downloadFile`.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const mockGet = vi.hoisted(() => vi.fn())
const mockProposalPdf = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api')
  return {
    ...actual,
    api: { ...actual.api, get: mockGet },
    exportApi: { proposalPdf: mockProposalPdf },
  }
})

import { ApiError, downloadFile } from '@/lib/api'
import { ProposalsPage } from '../index'

const PROPOSAL = {
  id: 4,
  title: 'Excel perfectionnement',
  description: 'Tableaux croisés dynamiques.',
  hours_estimated: 21,
  certification_suggestions: null,
  based_on: null,
  status: 'proposed' as const,
  created_at: '2026-03-04T10:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGet.mockResolvedValue([PROPOSAL])
  mockProposalPdf.mockResolvedValue(undefined)
})

describe('Page Propositions — bouton export', () => {
  it('expose un bouton d’export par proposition (G6)', async () => {
    render(<ProposalsPage />)
    await waitFor(() => expect(screen.getByText('Excel perfectionnement')).toBeInTheDocument())

    expect(
      screen.getByRole('button', { name: 'Exporter « Excel perfectionnement » en PDF' }),
    ).toBeInTheDocument()
  })

  it('déclenche l’export de la bonne proposition', async () => {
    render(<ProposalsPage />)
    await waitFor(() => expect(screen.getByText('Excel perfectionnement')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /Exporter/ }))

    await waitFor(() => expect(mockProposalPdf).toHaveBeenCalledWith(4))
  })

  it('affiche l’échec sans casser la page', async () => {
    mockProposalPdf.mockRejectedValue(new ApiError(500, 'Échec de la génération du PDF.'))
    render(<ProposalsPage />)
    await waitFor(() => expect(screen.getByText('Excel perfectionnement')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /Exporter/ }))

    await waitFor(() =>
      expect(
        screen.getByText('Export impossible : Échec de la génération du PDF.'),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText('Excel perfectionnement')).toBeInTheDocument()
  })
})

describe('downloadFile', () => {
  const originalFetch = globalThis.fetch
  let createdUrl: string | null = null
  let revoked: string[] = []

  beforeEach(() => {
    createdUrl = 'blob:mock-url'
    revoked = []
    URL.createObjectURL = vi.fn(() => createdUrl!) as unknown as typeof URL.createObjectURL
    URL.revokeObjectURL = vi.fn((url: string) => {
      revoked.push(url)
    }) as unknown as typeof URL.revokeObjectURL
  })

  afterEach(async () => {
    globalThis.fetch = originalFetch
    // La révocation est différée d'un tick : la laisser s'exécuter ici, sinon
    // elle retombe dans le test suivant et fausse ses compteurs.
    await new Promise((resolve) => setTimeout(resolve, 0))
  })

  function mockPdfResponse(disposition?: string): void {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(disposition ? { 'content-disposition': disposition } : {}),
      blob: async () => new Blob(['%PDF-1.7'], { type: 'application/pdf' }),
    }) as unknown as typeof fetch
  }

  it('utilise le nom de fichier fourni par le serveur', async () => {
    mockPdfResponse('attachment; filename="proposition-4-excel.pdf"')
    const clicked: string[] = []
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.push(this.download)
    })

    await downloadFile('/export/proposals/4.pdf', 'repli.pdf')

    expect(clicked).toEqual(['proposition-4-excel.pdf'])
  })

  it('retombe sur le nom fourni si le serveur n’en donne pas', async () => {
    mockPdfResponse()
    const clicked: string[] = []
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.push(this.download)
    })

    await downloadFile('/export/proposals/4.pdf', 'repli.pdf')

    expect(clicked).toEqual(['repli.pdf'])
  })

  it('révoque l’URL objet — après le tick, pas pendant le clic', async () => {
    mockPdfResponse('attachment; filename="x.pdf"')
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    await downloadFile('/export/proposals/4.pdf', 'repli.pdf')

    // Révoquer dans le même tick que le clic annule le téléchargement sur
    // certains navigateurs : la révocation doit être différée.
    expect(revoked).toEqual([])
    await waitFor(() => expect(revoked).toEqual(['blob:mock-url']))
    expect(document.querySelector('a[download]')).toBeNull()
  })

  it('propage une ApiError quand le serveur refuse', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: new Headers(),
      json: async () => ({ detail: 'Proposition introuvable.' }),
    }) as unknown as typeof fetch

    await expect(downloadFile('/export/proposals/99.pdf', 'repli.pdf')).rejects.toThrow(
      'Proposition introuvable.',
    )
  })
})
