import { Lightbulb } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function ProposalsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Propositions</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <Lightbulb className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Nouveaux cours proposés</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Ce module présentera les propositions générées automatiquement avec
            estimation d'heures, pistes de certification et options d'export PDF/Word.
            Disponible en Phase 1.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
