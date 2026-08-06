# AGENTS.md — Ask mode

This file provides guidance to agents when working with code in this repository.

## Product

**LunaYield Mission Lab** — IBM Space Exploration Hackathon. An interactive lunar-rover operations
and mission-planning platform. A rover has limited battery, storage, communication windows, and
multiple science targets. The system forecasts resource risks, detects anomalies, generates
mission strategies, converts them into executable plans, rejects unsafe plans, optimizes valid
plans, and recommends the plan with the greatest scientific value. A human operator approves
before any plan is executed.

## Confirmed Tech Stack

**Backend:** Python 3.12 · FastAPI · Pydantic · SQLModel · SQLite · FastAPI WebSockets
**Frontend:** React · TypeScript · Vite · Tailwind CSS · shadcn/ui · Zustand · TanStack Query · Recharts · Three.js · React Three Fiber · Drei
**Testing:** Pytest (backend) · Vitest (frontend) · Playwright (e2e)

## AI Decision Pipeline (in order)

1. Deterministic baseline forecasting
2. IBM Granite TTM adapter *(deferred — not yet implemented)*
3. Deterministic anomaly rules + Isolation Forest
4. IBM Granite structured strategy generation *(deferred — not yet implemented)*
5. Strict Pydantic validation of every model response
6. OR-Tools / NetworkX optimization *(deferred — not yet implemented)*
7. Deterministic Python safety verifier
8. Optional Z3 formal verification *(deferred — until basic verifier works)*

## Repository Responsibilities

| Directory        | Responsibility |
|------------------|----------------|
| `backend/`       | FastAPI server, WebSockets, domain services, simulation, planning, optimization, safety verification, SQLite persistence |
| `frontend/`      | React/Vite/TypeScript browser app, 3-D visualization |
| `datasets/`      | Small processed demo assets and provenance metadata only — no large raw datasets in Git |
| `preprocessing/` | Offline terrain, imagery, slope, traversability, and embedding preparation — not part of the deployed backend |
| `evaluation/`    | Baseline planner, evaluation scenarios, metrics, comparison results |
| `docs/`          | Architecture, AI methodology, safety, data sources, testing, demo instructions, Bob evidence |

## Deferred — Not Yet Implemented

The following are planned but must not be described as currently working:
Granite TTM · Granite mission reasoning · OR-Tools optimization · Three.js terrain rendering ·
Real NASA / lunar data · DINOv2 embeddings · Docker · Cloud deployment · Z3 formal verification

## Explicit Exclusions — Not Part of This System

Authentication · Payments · Teams · Multiple rovers · Full-Moon visualization · Complex physics ·
Voice assistant · General-purpose chatbot · Blockchain · Mobile application · Multi-agent
framework

## Bob Evidence

IBM Bob is the primary development tool. Architecture decisions, implementation contributions,
bugs found, tests generated, and validation results are recorded in `docs/bob-development-log.md`
(created when documentation files are introduced).
