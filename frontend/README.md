# CustomerPulse AI — Frontend

Enterprise-grade dashboard for a customer churn prediction model, built with React, Vite, and Tailwind CSS.

## Stack

- **React 19 + Vite + TypeScript**
- **Tailwind CSS** with a custom dark-first design system (HSL tokens in `src/index.css`)
- **shadcn/ui-style primitives** hand-built on Radix UI (`src/components/ui`)
- **framer-motion** for entrance/interaction animation
- **recharts** for the metrics bar chart and radial ROC-AUC gauge
- **react-hook-form + zod** for the churn prediction form
- **axios** for API calls, **sonner** for toasts
- **react-router-dom** for routing, with route-level code splitting

## Getting started

```bash
npm install
cp .env.example .env   # set VITE_API_BASE_URL to your FastAPI backend
npm run dev
```

Build for production: `npm run build` (type-checks with `tsc -b`, then bundles with Vite).

## Project structure

```
src/
  components/
    ui/          shadcn-style primitives (Button, Card, Select, Tabs, ...)
    layout/      AppShell, Sidebar, Topbar, ThemeToggle
    dashboard/   KpiCard, RiskBadge, PredictionResultPanel, ConfusionMatrix, ...
    forms/       PredictionForm and its field helpers
    charts/      recharts wrappers (bar chart, radial gauge)
  pages/         Landing, Predict, Metrics, Activity, ModelInfo
  services/      api.ts — axios client + per-endpoint fallback logic
  hooks/         useApiResource — fetch/loading/error state for GET endpoints
  lib/           cn(), zod schemas, risk-level helpers, formatters
  data/          mock data seeded from backend/reports/model_metrics.json
  context/       ThemeProvider (class/attribute-based dark/light, no next-themes)
  types/         Shared request/response/domain types
```

## Backend integration

The app expects a FastAPI backend exposing:

- `GET /health`
- `POST /predict` — see `src/types/index.ts` for the exact request/response shape
- `GET /metrics`
- `GET /model-info`
- `GET /recent-predictions`

At the time of writing, only the ML pipeline exists in `backend/` — none of these
routes are implemented yet. Every call in `src/services/api.ts` is wrapped in
`withFallback()`: it tries the real endpoint first and, on any failure, falls
back to realistic mock data seeded from the actual trained model's evaluation
report (`backend/reports/model_metrics.json`). Each fallback site has a
`TODO(backend)` comment. The UI always shows a "Live data" / "Demo data" badge
in the topbar so it's never ambiguous which source is active — nothing is
silently faked.

Once the backend implements these routes, no frontend changes are required;
traffic will switch to live data automatically.
