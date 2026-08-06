# AGENTS.md — Plan mode

This file provides guidance to agents when working with code in this repository.

## Product

**LunaYield Mission Lab** — an interactive lunar-rover operations and mission-planning platform.
The rover has limited battery, storage, communication windows, and multiple science targets. The
system forecasts resource risks, detects anomalies, generates mission strategies, converts them
into executable plans, rejects unsafe plans, optimizes valid plans, and recommends the plan with
the greatest scientific value. The operator must approve before any plan is executed.

## Confirmed Architecture

**Backend:** Python 3.12 · FastAPI · Pydantic · SQLModel · SQLite · FastAPI WebSockets
**Frontend:** React · TypeScript · Vite · Tailwind CSS · shadcn/ui · Zustand · TanStack Query · Recharts · Three.js · React Three Fiber · Drei
**Testing:** Pytest · Vitest · Playwright

## Repository Responsibilities

| Directory        | Responsibility |
|------------------|----------------|
| `backend/`       | FastAPI server, WebSockets, domain services, simulation, planning, optimization, safety verification, SQLite persistence |
| `frontend/`      | React/Vite/TypeScript browser app, 3-D visualization |
| `datasets/`      | Small processed demo assets and provenance metadata only — no large raw datasets |
| `preprocessing/` | Offline-only data preparation — never runs inside the deployed backend |
| `evaluation/`    | Baseline planner, evaluation scenarios, metrics, comparison results |
| `docs/`          | Architecture, AI methodology, safety, data sources, Bob evidence log |

## Required MVP Flow (10 steps)

1. Load one predefined mission.
2. Start synthetic rover telemetry.
3. Inject a battery anomaly.
4. Forecast a future battery-reserve violation.
5. Generate three candidate strategies.
6. Convert strategies into executable candidate plans.
7. Reject at least one plan using deterministic safety constraints.
8. Return all candidates to the frontend; display rejected plans as disabled with their
   constraint violations and explanatory metadata visible.
9. Rank and recommend only valid plans.
10. Require human operator approval.
11. Update route, downlink queue, and audit trail.

Every plan must pass through all eleven steps. Do not skip the rejection or display steps.

## AI Decision Pipeline — Confirmed Sequence

1. Deterministic baseline forecasting
2. IBM Granite TTM adapter *(deferred)*
3. Deterministic anomaly rules + Isolation Forest
4. IBM Granite structured strategy generation *(deferred)*
5. Strict Pydantic validation of every model response
6. OR-Tools / NetworkX optimization *(deferred)*
7. Deterministic Python safety verifier
8. Optional Z3 formal verification *(deferred)*

## Architectural Constraints

- `preprocessing/` is **offline/batch only** — it must never be imported or called by the
  deployed backend at request time.
- The backend is **authoritative** for plan validity and approval; the frontend is display-only
  for this decision.
- Safety verification must remain in a **separate module** from any LLM reasoning; they must not
  share state.
- Raw LLM output must **never** directly mutate mission state.
- Every model response must pass Pydantic validation before any downstream use.

## Phase Discipline

- Work in small, independently testable phases.
- Before proposing implementation, state: proposed files, intended behavior, risks, and validation
  commands.
- Wait for explicit approval before implementation when asked to plan.
- Never silently expand the approved scope.
- Every completed phase must leave the repository buildable and all tests green.
- Tests must accompany each phase; normal tests must not download large models or datasets.

## Deferred Features — Do Not Plan Until Vertical MVP Works

Granite TTM · Granite mission reasoning · OR-Tools optimization · Three.js terrain rendering ·
Real NASA / lunar data · DINOv2 embeddings · Docker · Cloud deployment · Z3 formal verification

## Explicit Exclusions — Out of Scope

Authentication · Payments · Teams · Multiple rovers · Full-Moon visualization · Complex physics ·
Voice assistant · General-purpose chatbot · Blockchain · Mobile application · Multi-agent
framework
