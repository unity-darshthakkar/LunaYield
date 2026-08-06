# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project

**LunaYield Mission Lab** — IBM Space Exploration Hackathon. An interactive lunar-rover operations
and mission-planning platform. A rover has limited battery, storage, communication windows, and
multiple science targets. The system forecasts resource risks, detects anomalies, generates
alternative mission strategies, converts them into executable plans, deterministically rejects
unsafe plans, optimizes valid plans, and recommends the plan that returns the greatest scientific
value.

IBM Bob is the primary development tool. Preserve clear evidence of Bob's contributions throughout
development. Record prompts, plans, implementations, bugs, tests, and commit hashes in
`docs/bob-development-log.md` (created when documentation files are introduced; updated at the end
of every completed phase).

## Repository Layout

| Directory        | Responsibility |
|------------------|----------------|
| `backend/`       | FastAPI server, WebSockets, domain services, simulation, planning, optimization, safety verification, SQLite persistence |
| `frontend/`      | React/Vite/TypeScript browser app, 3-D visualization |
| `datasets/`      | Small processed demo assets and provenance metadata only — no large raw datasets in Git |
| `preprocessing/` | Offline terrain, imagery, slope, traversability, and embedding preparation — never runs inside the deployed backend |
| `evaluation/`    | Baseline planner, evaluation scenarios, metrics, comparison results |
| `docs/`          | Architecture, AI methodology, safety, data sources, testing, demo instructions, Bob evidence |

## Tech Stack

**Backend:** Python 3.12 · FastAPI · Pydantic · SQLModel · SQLite · FastAPI WebSockets
**Frontend:** React · TypeScript · Vite · Tailwind CSS · shadcn/ui · Zustand · TanStack Query · Recharts · Three.js · React Three Fiber · Drei
**Testing:** Pytest (backend) · Vitest (frontend) · Playwright (e2e)

## Build / Lint / Test Commands

> Commands below are **planned** — update this section once the relevant config files exist.

```bash
# Backend
cd backend
pip install -e ".[dev]"           # planned: pyproject.toml
ruff check . && ruff format .     # planned: ruff.toml / pyproject.toml
pytest                            # run all backend tests
pytest tests/path/test_file.py::test_name   # run a single test

# Frontend
cd frontend
npm install                       # planned: package.json
npm run lint                      # planned: eslint config
npm run test                      # Vitest
npx vitest run src/path/file.test.ts   # single test file
npx playwright test               # e2e
```

## Code Style

> Configurations are **planned** — update once linter configs are committed.

- **Python:** Ruff for lint and formatting (Black-compatible line length 88); type annotations
  required on all public functions; Pydantic models for every data boundary.
- **TypeScript:** ESLint + Prettier; strict mode enabled; no `any`; named exports preferred.
- **Naming:** `snake_case` in Python, `camelCase`/`PascalCase` in TypeScript following React
  conventions.

## AI Decision Pipeline (in order)

1. Deterministic baseline forecasting
2. IBM Granite TTM adapter *(deferred — not yet implemented)*
3. Deterministic anomaly rules + Isolation Forest
4. IBM Granite structured strategy generation *(deferred — not yet implemented)*
5. Strict Pydantic validation of every model response
6. OR-Tools / NetworkX optimization *(deferred — not yet implemented)*
7. Deterministic Python safety verifier
8. Optional Z3 formal verification *(deferred — until basic verifier works)*

## Safety Invariants — Never Violate

- Raw LLM output must **never** directly mutate mission state.
- Every model response must pass strict Pydantic validation; retry malformed output at most once;
  always fall back to deterministic behavior.
- Safety verification must remain **separate** from LLM reasoning.
- The backend is authoritative for plan validity and approval.
- Invalid plans may be returned to the frontend and displayed as clearly rejected candidates;
  they must include deterministic constraint violations and explanatory metadata.
- Invalid plans must never be recommended, approved, or executed.
- The frontend must render rejected plans as disabled and visibly unsafe.

## Phase Discipline

- Work in small, independently testable phases.
- Inspect relevant files before editing any file.
- Before implementing a phase, report proposed files, behavior, risks, and validation commands.
- Wait for explicit approval before implementing when asked to plan.
- Never silently expand the approved scope.
- Tests must accompany each phase.
- Every completed phase must leave the repository buildable and testable.
- Normal tests must not download large models or datasets.

## Deferred Features

Do not implement until the vertical MVP demonstration works:

Granite TTM · Granite mission reasoning · OR-Tools optimization · Three.js terrain rendering ·
Real NASA / lunar data · DINOv2 embeddings · Docker · Cloud deployment · Z3 formal verification

## Explicit Exclusions

Authentication · Payments · Teams · Multiple rovers · Full-Moon visualization · Complex physics ·
Voice assistant · General-purpose chatbot · Blockchain · Mobile application · Multi-agent
framework

## What Never to Commit

Secrets · `.env` files · `node_modules/` · build output · model weights · large raw datasets ·
caches · unintended local databases
