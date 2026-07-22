# Actenon Cloud — Web UI

A modern React frontend for Actenon Cloud, the managed control plane.
Consumes the existing FastAPI API. Built fresh — the legacy `/pilot` pages
remain untouched as a fallback.

## Stack

- React 18 + TypeScript (strict) + Vite
- Tailwind CSS with semantic design tokens (dark mode default)
- TanStack Query for data fetching
- React Router
- Zod schemas mirroring the real backend response shapes
- Vitest + Testing Library for tests

## Design

A precision instrument — security console meets clean fintech. Not a
playful SaaS. Semantic tokens: `--allow`, `--deny`, `--pending`, `--neutral`,
`--surface`, `--ink`, `--edge`. Monospace for hashes, codes, amounts, and
machine values. WCAG AA contrast on every token pair.

## Screens

1. **Trust Surface** (`/app`) — the hero. A single consequential action as a
   vertical narrative: request → authority → decision → mutation-refused →
   tamper-evident receipt. Includes a "replay demo" canned incident.
2. **Review Queue** (`/app/review`) — human-in-the-loop approvals.
   Keyboard-operable (j/k to move, a/d to act).
3. **Action Ledger** (`/app/ledger`) — dense, sortable table with structured
   `failure_code` filtering. Click-through to the Trust Surface.
4. **Styleguide** (`/app/styleguide`) — tokens + core components.

## Development

```bash
cd web
npm install
npm run dev          # Vite dev server on :5173, proxies /api to :8000
npm run build        # tsc + vite build → dist/
npm run lint
npm run typecheck
npm test             # Vitest smoke tests
```

## Serving

The built SPA is served by the FastAPI app under `/app` with SPA fallback.
The legacy `/pilot` pages remain at their original paths.

## Auth

In development, paste a dev operator token via the "Dev auth" bar in the
top bar. Obtain a token via `POST /api/v1/auth/dev/operator-token`. In
production, OIDC sets the bearer token.

## Money

All monetary values are integer minor units end to end. The backend stores
Decimal as integer minor units. The frontend formats via a single money util
(`src/lib/money.ts`) that uses BigInt internally — no float is ever
introduced on the client.

## ROADMAP (explicitly deferred)

These platform-breadth features are NOT built. Extension points exist in
the API client and router:

- Tenant administration UI
- Policy / grant authoring UI
- Org-wide dashboards / analytics
- Billing
- User management
- Per-tenant settings

These are left as clean extension points, not implementations.
