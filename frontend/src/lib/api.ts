// Client HTTP centralisé — toutes les requêtes passent ici
// Cookies JWT httpOnly envoyés automatiquement via credentials: 'include'

/// <reference types="vite/client" />

const BASE_URL = (import.meta.env['VITE_API_URL'] as string | undefined) ?? 'http://localhost:8000'

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
  category: string
  status: 'active' | 'archived'
  enrolled_count: number
  dropout_count: number
  popularity_score: number
  year: number
  hours_estimated: number | null
  notes: string | null
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

export interface Favorite {
  id: number
  user_id: number
  course_id: number | null
  market_course_id: number | null
  created_at: string
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
