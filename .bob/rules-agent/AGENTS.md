# AGENTS.md — Agent (coding) mode

This file provides guidance to agents when working with code in this repository.

## Stack — Locked

**Backend:** Python 3.12 · FastAPI · Pydantic · SQLModel · SQLite · FastAPI WebSockets
**Frontend:** React · TypeScript · Vite · Tailwind CSS · shadcn/ui · Zustand · TanStack Query · Recharts · Three.js · React Three Fiber · Drei
**Backend tests:** Pytest · **Frontend tests:** Vitest · **E2E:** Playwright
**Python tooling:** Ruff (lint + format, Black-compatible 88-char lines)
**TypeScript tooling:** ESLint + Prettier, strict mode, no `any`

## Directory Ownership

| Directory        | Concrete responsibility |
|------------------|-------------------------|
| `backend/`       | FastAPI app, WebSockets, domain services, simulation, planning, optimization, safety verification, SQLite persistence |
| `frontend/`      | React/Vite/TypeScript browser app, 3-D visualization |
| `datasets/`      | Small processed demo assets and provenance metadata only — no large raw datasets |
| `preprocessing/` | Offline-only data preparation — never imported by the deployed backend |
| `evaluation/`    | Baseline planner, eval scenarios, metrics, comparison results |
| `docs/`          | Architecture, AI methodology, safety, data sources, Bob evidence log |

## Safety Rules — Never Violate

- Raw LLM output must **never** directly mutate mission state.
- Every model response must pass strict Pydantic validation before any downstream use.
- Retry malformed model output at most **once**; always fall back to deterministic behavior.
- Safety verification logic must remain in its own module, **separate** from any LLM reasoning.
- The backend is authoritative for plan validity and approval — the frontend never makes that call.
- Invalid plans may be returned to the frontend and displayed as clearly rejected candidates;
  they must carry deterministic constraint violations and explanatory metadata.
- Invalid plans must never be recommended, approved, or executed.
- The frontend must render rejected plans as disabled and visibly unsafe.

## AI Pipeline — Implementation Order

Implement stages in this order; do not skip ahead:

1. Deterministic baseline forecasting
2. Granite TTM adapter slot *(deferred — stub only until MVP demo works)*
3. Deterministic anomaly rules + Isolation Forest
4. Granite strategy generation *(deferred — stub only until MVP demo works)*
5. Pydantic validation layer for every model response
6. OR-Tools / NetworkX optimization *(deferred — stub only until MVP demo works)*
7. Deterministic Python safety verifier
8. Z3 formal verification *(deferred — only after basic verifier passes)*

## Phase Implementation Rules

- Inspect relevant files **before** editing any file.
- Before implementing a phase, state: proposed files, intended behavior, risks, and validation commands.
- Wait for explicit approval before writing code when asked to plan.
- Never silently expand the approved scope — surface scope questions first.
- Tests must accompany every phase; no phase ships without them.
- Normal tests must not download large models or datasets.
- Every completed phase must leave the repository buildable and all existing tests green.

## Commit Hygiene

Never commit: secrets · `.env` files · `node_modules/` · build output · model weights ·
large raw datasets · caches · unintended local databases.

## Bob Evidence

Update `docs/bob-development-log.md` at the end of every completed phase. Record the Bob prompts
used, plans generated, files implemented, bugs found, tests written, and the relevant commit hash.
(Create the file when documentation files are first introduced.)
