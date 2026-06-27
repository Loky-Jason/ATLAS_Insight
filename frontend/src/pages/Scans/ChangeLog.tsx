import { History } from 'lucide-react'

export function ChangeLogPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <History className="mb-4 h-12 w-12 text-muted-foreground/40" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-foreground">Journal des modifications</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Historique des changements détectés entre les scans.
      </p>
    </div>
  )
}
