import { Archive } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function ArchivesPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Archives</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <Archive className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Historique des cours archivés</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Ce module permettra de consulter les cours fermés, de les restaurer
            ou de les exporter. Disponible en Phase 2.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
