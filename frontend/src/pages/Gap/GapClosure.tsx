import { XCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function GapClosurePage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Recommandations — À fermer</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <XCircle className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Cours SCAP candidats à la fermeture</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Cours non dispensés par les écoles suivies. Analysez et approuvez leur archivage.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
