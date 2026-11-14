# Web interface

Docker Compose serves the site with nginx and proxies `/api` to the .NET API. Outside Docker, the .NET API serves the site directly; the standalone Node static server does not proxy API requests. See the [project setup](../README.md) for prerequisites, startup, data definitions, and API details.

The rankings and movement views share season, week, and EPA metric selections when navigating between them. Both show the latest entered week and refresh status. Team logos and colors come from nflverse; abbreviated badges remain visible if a logo cannot load. Teams with no qualifying plays are omitted until data is available. `src/data.ts` is retained only as a fixture for the existing sample-data tests; the live interface does not use it.

Run `npm ci` and `npm run build` in this directory before starting the .NET server locally. The TypeScript compiler emits browser modules to `dist`; rebuild after changes. Docker builds the frontend automatically. Run `npm test` to build and run the frontend unit tests. On narrow screens, scroll the table and movement chart horizontally.
