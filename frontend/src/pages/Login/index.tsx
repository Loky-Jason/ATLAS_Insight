import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setErrorMsg(null)
    setIsSubmitting(true)

    try {
      await login({ email, password })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        // Message backend (ex. "Identifiants incorrects")
        setErrorMsg(err.message)
      } else {
        setErrorMsg('Une erreur inattendue est survenue.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">
            ATLAS<span className="text-primary"> Insight</span>
          </CardTitle>
          <CardDescription>
            Connectez-vous pour accéder au tableau de bord pédagogique.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={(e) => void handleSubmit(e)} noValidate className="space-y-4">
            {/* Email */}
            <div className="space-y-2">
              <Label htmlFor="email">Adresse e-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="coordinateur@scap.paris"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                aria-describedby={errorMsg ? 'login-error' : undefined}
              />
            </div>

            {/* Mot de passe */}
            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {/* Message d'erreur */}
            {errorMsg !== null && (
              <p
                id="login-error"
                role="alert"
                className="rounded-md bg-destructive/20 px-3 py-2 text-sm text-destructive-foreground"
              >
                {errorMsg}
              </p>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={isSubmitting || email === '' || password === ''}
            >
              {isSubmitting ? 'Connexion en cours...' : 'Se connecter'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
