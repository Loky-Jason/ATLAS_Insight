import { PlusCircle } from 'lucide-react'

export function GapCreationPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <PlusCircle className="mb-4 h-12 w-12 text-muted-foreground/40" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-foreground">Recommandations — À créer</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Formations du marché non proposées par SCAP, candidates à la création.
      </p>
    </div>
  )
}
