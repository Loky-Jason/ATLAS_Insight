import type { AnalyticsPopularity } from '@/lib/api'

// Données mock utilisées quand le backend est inaccessible
// Clairement identifiées pour l'utilisateur (badge "Données de démonstration")
const MOCK_MOST = [
  { title: 'Anglais professionnel B2', popularity_score: 94, enrolled_count: 42, dropout_count: 3 },
  { title: 'Excel avancé — tableaux croisés', popularity_score: 88, enrolled_count: 38, dropout_count: 4 },
  { title: 'Management d\'équipe à distance', popularity_score: 82, enrolled_count: 35, dropout_count: 5 },
  { title: 'Prise de parole en public', popularity_score: 77, enrolled_count: 31, dropout_count: 6 },
  { title: 'Communication écrite professionnelle', popularity_score: 71, enrolled_count: 29, dropout_count: 4 },
]
const MOCK_LEAST = [
  { title: 'Initiation à l\'IA générative', popularity_score: 12, enrolled_count: 6, dropout_count: 4 },
  { title: 'Gestion du temps et priorisation', popularity_score: 18, enrolled_count: 9, dropout_count: 5 },
  { title: 'Droit du travail — bases', popularity_score: 23, enrolled_count: 11, dropout_count: 4 },
  { title: 'Comptabilité analytique', popularity_score: 27, enrolled_count: 13, dropout_count: 4 },
  { title: 'Bureautique LibreOffice', popularity_score: 31, enrolled_count: 15, dropout_count: 5 },
]

const withMeta = <T extends { title: string }>(arr: T[], startId: number) =>
  arr.map((item, i) => ({ ...item, id: startId + i, category: 'Bureautique' }))

export const MOCK_ANALYTICS: AnalyticsPopularity = {
  most_popular: withMeta(MOCK_MOST, 1),
  least_popular: withMeta(MOCK_LEAST, 11),
  total_courses: 47,
  total_enrolled: 824,
  total_dropouts: 97,
}
