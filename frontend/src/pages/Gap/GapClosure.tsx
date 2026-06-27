import { XCircle } from 'lucide-react'

export function GapClosurePage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <XCircle className="mb-4 h-12 w-12 text-muted-foreground/40" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-foreground">Recommandations — À fermer</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Cours SCAP candidates à la fermeture (non dispensés ailleurs).
      </p>
    </div>
  )
}
