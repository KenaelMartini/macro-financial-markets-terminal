# System Map

## Data Flow

Source -> Parsing -> Normalization -> Storage -> Analytics -> API -> UI

## Source Classification

- Core: IBKR, news feeds, central bank feed polling, calendar feed.
- Accessory: optional legacy central bank files, optional external NLP helper.

## Worker Responsibilities

- `news`: feed polling and persistence.
- `cb_poller`: central bank polling, excerpt extraction, NLP snapshot persistence.
- `calendar`: economic calendar refresh and persistence.
- `ibkr`: live market snapshots and candle retrieval.

## Failure Strategy

- All workers run under supervisor with restart/backoff counters.
- API status exposes worker and path health.
- `/health` returns degraded when path/db checks fail.
