# Disclaimer

This is what happens when you are too addicted to Github Copilot

# Power Index

An unofficial NFL rankings app backed by a .NET API and a Python engine using [nflreadpy](https://nflreadpy.nflverse.com/). It offers offensive, defensive, special-teams and combined EPA rankings, not a custom overall power ranking.

## Run with Docker Compose

Install Docker with the Compose plugin, start Docker, and run from the project root:

```sh
docker compose up --build
```

Open [http://localhost:5080](http://localhost:5080). To use a different host port, run `PORT=8080 docker compose up --build` (or set `PORT` in your environment on Windows). Stop the stack with Ctrl+C, then run `docker compose down` to remove its containers and network. After changing code, rebuild with `docker compose up --build`.

Compose runs three services: an nginx web server, the .NET API, and a Python engine service. Only the web port is published. The web server proxies `/api/` to the API, which calls the engine on the private Compose network. The engine persists SQLite at `data/rankings.sqlite3` via a bind mount; the directory must be writable by the engine container's `app` user (UID 1000). The engine's health check indicates that the service is listening, not that nflverse is reachable; data downloads require internet access. Initial refresh can take a while. View errors with `docker compose logs api engine`.

## Run locally without Docker

Prerequisites: .NET SDK 10, Python with `venv`, Node.js 20+, and an internet connection to nflverse. Node.js builds the TypeScript frontend into browser-ready JavaScript.

From the project root:

```sh
cd www
npm ci
npm run build
cd ..
python3 -m venv engine/.venv
engine/.venv/bin/python -m pip install -r engine/requirements.txt
engine/.venv/bin/python engine/service.py
```

In another terminal:

```sh
POWERINDEX_ENGINE_URL=http://localhost:8000 dotnet run --project api/PowerIndex.Api.csproj --urls http://localhost:5080
```

On Windows, use `py -m venv engine\.venv`, `engine\.venv\Scripts\python.exe -m pip install -r engine\requirements.txt`, and `engine\.venv\Scripts\python.exe engine\service.py`. Set `POWERINDEX_ENGINE_URL` to `http://localhost:8000` before starting the API. Run `npm run build` in `www` after changing frontend TypeScript; the .NET server serves the generated `www/dist` files. Docker builds those files automatically.

Open [http://localhost:5080](http://localhost:5080). The .NET server serves the site and calls the engine service. The engine checks nflverse on startup and every 24 hours after the previous attempt. It refreshes the latest season atomically, records when each new completed week is first entered, and retains the previous successful snapshot if an update fails. Other seasons are downloaded and stored on first request; they are not automatically refreshed. The interface displays the latest entered week, last successful refresh, and any refresh failure. The browser checks this status every minute; reload when a new week appears. Set `POWERINDEX_DB` to change the database path. The default CLI/subprocess mode still works, but scheduled updates require the engine service.

## Data and API

- `GET /api/seasons` returns available years since 2020 through the latest refreshed season.
- `GET /api/status` reports the latest entered season/week, when that week was first entered, last successful refresh, and any latest refresh error.
- `GET /api/rankings?season=2024` returns `{ "season": 2024, "weeks": { "1": { "offense": [...], "defense": [...], "special": [...], "combined": [...] }, ... } }`. Each row includes team ID, name, conference, division, colors, logo URL, record, rank, previous rank, movement, EPA value, qualifying play count (null for combined), `strengthOfSchedule` and `strengthOfScheduleRank`, season-to-date `points.for`, `points.allowed`, and `points.net`, and `games.current` / `games.previous` with opponent, home/away and team/opponent scores. A game has status `played`, `bye`, or `unavailable` (no previous week). Rows are ordered by rank. Null previous rank/movement means unavailable. Missing or invalid seasons and upstream failures return HTTP errors rather than sample data.

Combined EPA is selected by default unless the URL specifies a metric. Rankings initially show team and rank change, ordered by current rank. Click or tap a team row, or use its team button, to show or hide its selected and previous weeks' game details. Expanded rows remain open when sorting or filtering, and collapse when changing the week, season, or metric. Use **Columns** to add or remove stats including strength of schedule (SOS), rank, record, points, and the selected and previous calendar weeks' games. Click SOS to sort by toughest schedule first; click again to reverse the sort. Unavailable SOS values appear last in either direction. Column selections and sort preferences last until the page is reloaded and are retained when changing season, week, or EPA metric. Sort game columns alphabetically by opponent; byes and unavailable weeks appear last. Hiding the active sort column restores rank order. Scores are shown from each team's perspective, and points totals cover regular-season games through the selected week. On the movement page, click or tap a team row, or use its team button, to expand or collapse its game details; use **Expand all** or **Collapse all** to change all rows at once. Changing the week, season, or metric resets the rows to collapsed. Scroll horizontally on smaller screens to see all columns or the chart. Existing stored seasons are upgraded on first access by loading their schedules; if that download fails, the original snapshot is retained and an error is returned.

The **History** page compares weekly EPA ranks for selected teams on one chart, with better ranks at the top. Its rank axis fits all rankings of selected teams across available weeks, with one rank of padding where possible; it returns to 1–32 when no teams are selected. All teams are initially selected; use the division-grouped checkboxes, **Select all**, or **Clear all** to choose which lines to show. Hover over a point to see its team, week, and rank. Click a line or point to highlight its team and dim the others; click it again or use **Clear highlight** to reset. Highlighting does not change the axis. Selected teams also have a **Focus** button for the same action via keyboard. The selected week is marked, but the chart always shows all available weeks. The expandable table contains exact ranks; gaps indicate weeks where a team has no ranking. Team selections and highlights are retained when changing metric or week if the team remains ranked, and reset when changing season.

For each regular-season week, every scheduled game must have a score and at least one play with EPA before the week is entered. Weeks after an incomplete week are withheld. This verifies presence, not completeness, of upstream play-by-play; nflverse may revise data later. A week is cumulative through that week.

Offense and defense average non-null, finite EPA on run and pass plays, excluding deleted plays, kneels and spikes. Defense is EPA allowed, so lower is better. Special teams averages EPA on kickoffs, punts, field goals and extra points, excluding deleted plays; it credits the play's possession team with EPA and its opponent with the negative EPA. nflverse identifies the receiving team as possession on kickoffs, but the kicking team on punts and kicks from scrimmage. Two-point attempts and special-teams plays without EPA are excluded. Higher special-teams EPA is better. Combined is offensive EPA/play minus defensive EPA/play allowed plus net special-teams EPA/play; its components have different play counts and this is not a single per-play average. Teams missing a component are omitted from combined rankings. Equal unrounded values are ordered by team abbreviation. Records include wins, losses and ties through the selected week. Rank movement compares with the immediately preceding week only. Display values are rounded; ranks use full precision.

Strength of schedule is the average, over every regular-season game played through the selected week, of each opponent's offensive EPA/play minus defensive EPA/play allowed through that same selected week. Repeated opponents count once per game; byes do not count. The SOS column displays each team's league-wide rank by this value, with #1 being the toughest schedule. Rankings use full precision and break equal values by team abbreviation, matching the EPA ranking convention. The rank is calculated before filters, includes teams with calculable SOS even if they are missing from the selected EPA view, and is identical across views. SOS excludes special teams, unlike the combined EPA index. Both the value and rank are `null` (displayed as a dash) if the team has played no games or any opponent lacks either EPA component.

Team names, colors, logos, schedules, and play-by-play come from nflverse through nflreadpy. Data may be delayed or revised upstream. Seasons begin at 2020 to use current team identities consistently. Playoff games are excluded.

## Tests

```sh
engine/.venv/bin/python -m unittest discover -s engine -p 'test_*.py'
dotnet build api/PowerIndex.Api.csproj
cd www && npm test
```

The engine tests use small synthetic games and plays. The frontend tests include the original demo snapshots as fixtures; they are not used by the live site.
