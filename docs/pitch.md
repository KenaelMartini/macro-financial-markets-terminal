# 2-Minute Technical Pitch

## Problem

Macro desks need one place to track central bank communication, market reaction, and risk posture without juggling many tools.

## Solution

This terminal ingests live macro/news/CB/market streams, normalizes payloads, persists history in SQLite, computes analytics, and exposes both API and UI views for operational monitoring.

## Architecture

- Worker ingestion for news, central banks, calendar, and IBKR.
- Persistent storage with replay endpoints.
- Analytics for tone, signals, risk, and reports.
- FastAPI transport and browser UI.
- Health/status endpoints for operations.

## Why this stack

- FastAPI: fast iteration and typed API boundaries.
- SQLite: simple local persistence for deterministic demo and low ops overhead.
- IBKR integration: direct broker-grade market feed path.

## Limits and next steps

- Some analytics are proxy heuristics.
- Live quality depends on IBKR entitlements/connectivity.
- Planned progression: stronger validation, richer risk models, production deployment hardening.
