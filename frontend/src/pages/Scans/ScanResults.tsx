import { FileSearch } from 'lucide-react'

export function ScanResultsPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <FileSearch className="mb-4 h-12 w-12 text-muted-foreground/40" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-foreground">Résultats de scan</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Visualisez ici les résultats du dernier scan multi-école.
      </p>
    </div>
  )
}
