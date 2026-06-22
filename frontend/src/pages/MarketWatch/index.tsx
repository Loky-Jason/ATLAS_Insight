import { TrendingUp } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function MarketWatchPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Veille marché</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <TrendingUp className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Veille automatisée</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Ce module agrégera les cours proposés par d'autres écoles parisiennes,
            avec score de pertinence et explication. Disponible en Phase 1.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
