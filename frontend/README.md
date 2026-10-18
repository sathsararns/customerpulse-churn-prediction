# CustomerPulse AI dashboard

Run `npm run dev` from this directory after starting the backend on port 8000.
The dashboard reads prediction results, metrics, model metadata, history, health,
tracking connectivity and recorded training stages from the API.

## Live and demo modes

Copy `.env.example` to `.env.local` if you need to override settings:

```text
VITE_API_BASE_URL=http://localhost:8000
VITE_DEMO_MODE=false
```

Live mode is the default. API failures show an unavailable/error state and a
retry action; they never generate heuristic predictions or substitute sample
metrics. Set `VITE_DEMO_MODE=true` explicitly to use illustrated data and
heuristic predictions without making backend calls. Demo mode is labelled
throughout the dashboard. Restart the Vite dev server after changing these
settings; production builds need rebuilding.

Live risk badges use the backend's `risk_level`. Result panels and history show
the model version used for scoring. Metrics identify their model version, and
the model page only combines metrics with matching metadata. History rows from
before model-version recording show `Not recorded`.

The API loads a model once at startup. After activating a different version,
restart the API and refresh the dashboard. Health reports a pending restart;
the loaded version continues to identify predictions and metrics until then.
Tracking-store connectivity is separate from whether the MLflow UI is running.

Health, tracking connectivity and recorded pipeline stages refresh periodically.
The model page shows observed run stages and failures, including candidates
awaiting activation. No drift-monitoring status is claimed by this dashboard.

## Checks

```text
npm test
npm run build
npm run lint
```

The contract tests use Node's built-in TypeScript-capable test runner. They check
live failures, explicit demo isolation, backend risk/version preservation and form
validation. The production build also runs the TypeScript compiler.


## Docker

The root [setup guide](../README.md) starts the dashboard on port 5173.
The multi-stage image builds the app and serves it with unprivileged Nginx.
Browser calls use `/api` on the same origin, proxied to the backend service.
Docker builds always set `VITE_DEMO_MODE=false`; local `.env` files are excluded.
The prediction form accepts an optional customer ID. Activity uses stored
customer IDs and displays event IDs, model versions and prediction sources.
