import { Component, type ErrorInfo, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  message: string | null
}

/**
 * Capture les erreurs de rendu React pour éviter une page blanche.
 * Affiche un message FR + bouton de rechargement.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, message: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // Log non bloquant pour le diagnostic
    console.error('Erreur de rendu capturée par ErrorBoundary :', error, info.componentStack)
  }

  private handleReload = (): void => {
    window.location.reload()
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-6 text-center"
        >
          <h1 className="text-xl font-semibold text-foreground">Une erreur est survenue</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            L'affichage a rencontré un problème. Vous pouvez recharger la page. Si le problème
            persiste, contactez l'administrateur.
          </p>
          {this.state.message && (
            <p className="max-w-md break-words text-xs text-muted-foreground/70">
              Détail : {this.state.message}
            </p>
          )}
          <button
            type="button"
            onClick={this.handleReload}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Recharger la page
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
