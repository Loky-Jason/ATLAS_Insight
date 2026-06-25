# ATLAS Insight

## Product
Dashboard décisionnel pédagogique pour SCAP.paris. Outil interne Mairie de Paris pour gérer le catalogue de formations, analyser la popularité des cours, détecter les gaps d'offre via veille marché, générer des propositions de formation et exporter des bilans.

## Register
product — dashboard / admin tool / data analytics. Design SERVES the product.

## Audience
Agents SCAP.paris (service formation continue de la Mairie de Paris). Utilisation bureau quotidienne, PC, écran 1920×1080+. Internes Mairie, pas de public externe.

## Stack
React 18 + TypeScript strict + Vite 6 + Tailwind CSS 3 + shadcn/ui + Recharts. Backend FastAPI. Dark theme only.

## Design constraints
- Dark theme only (usage quotidien bureau, pas de light mode)
- Data-dense dashboard (KPI cards, tables, charts, filtres)
- Accessible WCAG AA
- Bundle minimal (PC peu performants Mairie)
- Textes UI en français
