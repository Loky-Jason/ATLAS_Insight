import { GraduationCap } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

export function SchoolsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Écoles suivies</h2>
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <GraduationCap className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium text-muted-foreground">Gestion des écoles</p>
          <p className="max-w-xs text-sm text-muted-foreground/70">
            Ajoutez, modifiez ou supprimez les écoles surveillées par le système de veille.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
