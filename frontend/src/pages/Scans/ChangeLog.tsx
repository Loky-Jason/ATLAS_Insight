import { History } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function ChangeLogPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Journal des modifications</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <History className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Historique des changements</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Suivi des modifications détectées automatiquement entre les scans.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
