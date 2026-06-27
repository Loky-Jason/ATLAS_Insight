import { PlusCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function GapCreationPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Recommandations — À créer</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <PlusCircle className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Formations à créer</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Formations du marché non proposées par SCAP, triées par pertinence.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
