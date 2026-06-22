import { BookOpen } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function CoursesPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Cours SCAP</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <BookOpen className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Liste des cours SCAP</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Ce module affichera la liste complète des cours avec leurs statistiques,
            filtres et options d'édition. Disponible en Phase 1.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
