# Power Index project instructions

## Project and architecture

- This is an unofficial NFL EPA rankings app. Keep the frontend modular and preserve the existing user experience unless a change is requested.
- Docker Compose runs nginx, the .NET API, and the Python engine. nginx serves the compiled TypeScript frontend and proxies `/api/` to the API; the API calls the engine over HTTP. The engine uses nflreadpy and stores season snapshots in SQLite. The API can also invoke Python as a subprocess in local fallback mode.
- `www/src/` contains the frontend source; `www/dist/` is generated. Keep TypeScript strict, use the existing shared types and helpers, and do not edit generated files. `www/src/data.ts` is a test fixture, not live data.
- `engine/engine.py` calculates snapshots, `engine/store.py` owns persistence and refresh, and `engine/service.py` serves engine endpoints and schedules refreshes. `api/Program.cs` exposes the public API.
- See [README.md](../README.md) for setup, API shapes, data definitions, and UI behavior; update it when behavior changes.

## Data invariants

- Rankings are season-to-date through the selected completed regular-season week. Defense is EPA allowed (lower is better). Combined is the play-weighted average of offense, negative defense allowed, and net special teams; it is not a custom overall power ranking.
- SOS averages each played opponent's offense minus defense allowed through the selected week. Count repeat opponents once per game; do not include special teams. Rank #1 is the toughest schedule. Preserve unavailable values rather than silently dropping opponents.
- Records, points, and game results include ties and represent completed games through the selected week. Preserve the existing treatment of byes and unavailable previous weeks.
- Keep snapshot upgrades and refreshes safe: retain prior stored data on failure and preserve the original week-entry timestamps. Avoid changing the user's SQLite database during tests; use temporary databases or an isolated copy.
- Garbage-time filtering was discussed but is not implemented. Do not silently change existing EPA calculations; agree on the filter and user-facing behavior before adding it.

## UI and verification

- Preserve the selected column and sort direction when changing season, week, or EPA metric. Rankings default to team and change, with other columns optional. Rankings and Movement rows expand to show current and previous game details; History plots overall or conference-relative weekly rankings.
- Run the smallest relevant tests. Frontend: `cd www && npm test` (builds TypeScript and runs Node tests). Engine: `engine/.venv/bin/python -m unittest discover -s engine -p 'test_*.py'`. API: `dotnet build api/PowerIndex.Api.csproj`.
- Docker builds the frontend automatically. For local .NET hosting, run `npm ci` and `npm run build` in `www`; rebuild after frontend changes. After updating a running Docker app, rebuild the affected service and reload the browser; stale browser code may require a hard reload.
