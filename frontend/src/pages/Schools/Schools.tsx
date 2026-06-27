import { GraduationCap } from 'lucide-react'

export function SchoolsPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <GraduationCap className="mb-4 h-12 w-12 text-muted-foreground/40" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-foreground">Écoles suivies</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Gérez les écoles surveillées par le système de veille.
      </p>
    </div>
  )
}
