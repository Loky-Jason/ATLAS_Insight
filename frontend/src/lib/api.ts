// Client HTTP centralisé — toutes les requêtes passent ici
// Cookies JWT httpOnly envoyés automatiquement via credentials: 'include'

/// <reference types="vite/client" />

const BASE_URL = (import.meta.env['VITE_API_URL'] as string | undefined) ?? 'http://localhost:8000/api/v1'

// ── Types génériques ──────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// ── Requête de base ───────────────────────────────────────────────────────────

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`

  let response: Response
  try {
    const isFormData = init.body instanceof FormData
    response = await fetch(url, {
      ...init,
      credentials: 'include',
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...init.headers as Record<string, string>,
      },
    })
  } catch (err) {
    // Erreur réseau (backend injoignable)
    throw new ApiError(0, 'Le serveur est inaccessible. Vérifiez que le backend est démarré.')
  }

  if (!response.ok) {
    let message = `Erreur ${response.status}`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // body non-JSON, on garde le message par défaut
    }
    throw new ApiError(response.status, message)
  }

  // 204 No Content
  if (response.status === 204) return undefined as unknown as T

  return response.json() as Promise<T>
}

// ── Méthodes HTTP publiques ───────────────────────────────────────────────────

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),

  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'POST',
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    }),

  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'PUT',
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    }),

  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'PATCH',
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    }),

  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),

  // Upload multipart (import fichier)
  upload: <T>(path: string, formData: FormData) =>
    request<T>(path, {
      method: 'POST',
      body: formData,
      headers: {}, // laisser le navigateur définir le Content-Type multipart
    }),
}

// ── Types domaine ─────────────────────────────────────────────────────────────

export interface User {
  id: number
  email: string
  role: string
}

export interface Course {
  id: number
  title: string
  category: string | null
  status: 'active' | 'archived'
  enrolled_count: number
  dropout_count: number
  popularity_score: number | null
  age_brackets: string | null
  year: number | null
  hours_estimated: number | null
  source: string
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CourseCreate {
  title: string
  category?: string | null
  status?: 'active' | 'archived'
  enrolled_count?: number
  dropout_count?: number
  year?: number | null
  hours_estimated?: number | null
  notes?: string | null
}

export interface CourseUpdate {
  title?: string
  category?: string | null
  status?: 'active' | 'archived'
  enrolled_count?: number
  dropout_count?: number
  year?: number | null
  hours_estimated?: number | null
  notes?: string | null
}

export interface PopularityEntry {
  title: string
  popularity_score: number
  enrolled_count: number
  dropout_count: number
}

export interface AnalyticsPopularity {
  most_popular: PopularityEntry[]
  least_popular: PopularityEntry[]
  total_courses: number
  total_enrolled: number
  total_dropouts: number
}

export interface MarketCourse {
  id: number
  title: string
  school: string | null
  source_url: string | null
  summary: string | null
  relevance_score: number | null
  why_it_works: string | null
  related_scap_course_id: number | null
  status: 'candidate' | 'reviewed' | 'adopted' | 'rejected'
  discovered_at: string
}

export interface MarketCourseCreate {
  title: string
  school?: string | null
  source_url?: string | null
  summary?: string | null
  relevance_score?: number | null
  why_it_works?: string | null
  related_scap_course_id?: number | null
  status?: MarketCourse['status']
}

export interface MarketCourseUpdate extends Partial<MarketCourseCreate> {}

export interface CourseProposal {
  id: number
  title: string
  description: string | null
  hours_estimated: number | null
  certification_suggestions: string | null
  based_on: string | null
  status: 'draft' | 'proposed' | 'exported'
  created_at: string
}

export interface CourseProposalCreate {
  title: string
  description?: string | null
  hours_estimated?: number | null
  certification_suggestions?: string | null
  based_on?: string | null
  status?: CourseProposal['status']
}

export interface CourseProposalUpdate extends Partial<CourseProposalCreate> {}

export interface Favorite {
  id: number
  user_id: number
  course_id: number | null
  market_course_id: number | null
  created_at: string
}

export interface FavoriteCreate {
  course_id?: number | null
  market_course_id?: number | null
}

export interface ImportResult {
  inserted: number
  errors: string[]
  filename: string
}

export interface AuditLogEntry {
  id: number
  user_id: number | null
  action: string
  target: string | null
  timestamp: string
}

// ── API helpers typés par domaine ─────────────────────────────────────────────

export const coursesApi = {
  list: (params?: { status?: string; category?: string; search?: string; year?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.category) qs.set('category', params.category)
    if (params?.search) qs.set('search', params.search)
    if (params?.year) qs.set('year', String(params.year))
    const query = qs.toString()
    return api.get<Course[]>(`/courses${query ? `?${query}` : ''}`)
  },
  get: (id: number) => api.get<Course>(`/courses/${id}`),
  create: (payload: CourseCreate) => api.post<Course>('/courses', payload),
  update: (id: number, payload: CourseUpdate) => api.patch<Course>(`/courses/${id}`, payload),
  archive: (id: number) => api.post<Course>(`/courses/${id}/archive`),
  restore: (id: number) => api.post<Course>(`/courses/${id}/restore`),
}

export const marketCoursesApi = {
  list: (params?: { status?: string; school?: string; search?: string }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.school) qs.set('school', params.school)
    if (params?.search) qs.set('search', params.search)
    const query = qs.toString()
    return api.get<MarketCourse[]>(`/market-courses${query ? `?${query}` : ''}`)
  },
  get: (id: number) => api.get<MarketCourse>(`/market-courses/${id}`),
  create: (payload: MarketCourseCreate) => api.post<MarketCourse>('/market-courses', payload),
  update: (id: number, payload: MarketCourseUpdate) =>
    api.patch<MarketCourse>(`/market-courses/${id}`, payload),
  delete: (id: number) => api.delete<void>(`/market-courses/${id}`),
}

export const proposalsApi = {
  list: (params?: { status?: string; search?: string }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.search) qs.set('search', params.search)
    const query = qs.toString()
    return api.get<CourseProposal[]>(`/proposals${query ? `?${query}` : ''}`)
  },
  get: (id: number) => api.get<CourseProposal>(`/proposals/${id}`),
  create: (payload: CourseProposalCreate) => api.post<CourseProposal>('/proposals', payload),
  update: (id: number, payload: CourseProposalUpdate) =>
    api.patch<CourseProposal>(`/proposals/${id}`, payload),
  delete: (id: number) => api.delete<void>(`/proposals/${id}`),
}

export const favoritesApi = {
  list: () => api.get<Favorite[]>('/favorites'),
  add: (payload: FavoriteCreate) => api.post<Favorite>('/favorites', payload),
  remove: (id: number) => api.delete<void>(`/favorites/${id}`),
}

export const auditLogsApi = {
  list: (params?: { skip?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.skip !== undefined) qs.set('skip', String(params.skip))
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    const query = qs.toString()
    return api.get<AuditLogEntry[]>(`/audit-logs${query ? `?${query}` : ''}`)
  },
}

export const importsApi = {
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.upload<ImportResult>('/imports', formData)
  },
}

// ── Helpers erreur ────────────────────────────────────────────────────────────

/** Traduit une ApiError en message FR lisible, avec cas 403 explicite. */
export function getErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return "Action non autorisée — droits administrateur requis."
    if (err.status === 409) return "Cet élément existe déjà."
    if (err.status === 404) return "Élément introuvable."
    if (err.status === 0) return "Le serveur est inaccessible. Vérifiez que le backend est démarré."
    return err.message
  }
  return "Une erreur inattendue est survenue."
}
