import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { api, ApiError, setOnUnauthorized, type User } from './api'

// ── Types ────────────────────────────────────────────────────────────────────

interface LoginCredentials {
  email: string
  password: string
}

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  error: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
}

// ── Contexte ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

// ── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Vérification de session au démarrage (cookie existant)
  useEffect(() => {
    let cancelled = false

    const checkSession = async () => {
      try {
        const me = await api.get<User>('/auth/me')
        if (!cancelled) setUser(me)
      } catch (err) {
        // 401 = pas de session active, c'est normal
        if (err instanceof ApiError && err.status === 401) {
          if (!cancelled) setUser(null)
        }
        // Erreur réseau : backend non démarré → pas de session
        if (!cancelled) setUser(null)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void checkSession()
    return () => { cancelled = true }
  }, [])

  // Déclencheur global : n'importe quelle requête API 401 déconnecte l'utilisateur.
  useEffect(() => {
    setOnUnauthorized(() => setUser(null))
  }, [])

  const login = useCallback(async ({ email, password }: LoginCredentials) => {
    setError(null)
    setIsLoading(true)
    try {
      const me = await api.post<User>('/auth/login', { email, password })
      setUser(me)
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : 'Une erreur inattendue est survenue'
      setError(message)
      throw err // re-throw pour que le formulaire puisse réagir
    } finally {
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      // On déconnecte côté client même si le serveur échoue
    } finally {
      setUser(null)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth doit être utilisé dans un <AuthProvider>')
  return ctx
}
