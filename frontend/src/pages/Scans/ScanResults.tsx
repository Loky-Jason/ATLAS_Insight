import { FileSearch } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function ScanResultsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Résultats de scan</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <FileSearch className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Derniers résultats multi-école</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Visualisez ici les différences détectées entre chaque scan et les cours SCAP.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
