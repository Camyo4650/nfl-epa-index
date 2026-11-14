import { errorMessage, requiredElement } from './dom.js';
import type { Metric, SeasonData, Selection, Status } from './types.js';

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    const body = await response.json().catch(() => null);
    if (body?.detail || body?.error) message = body.detail || body.error;
    throw new Error(message);
  }
  return response.json();
}

export async function setupDataControls(onChange: (selection: Selection | null) => void) {
  const season = requiredElement<HTMLSelectElement>('#season-select');
  const week = requiredElement<HTMLSelectElement>('#week-select');
  const metric = requiredElement<HTMLSelectElement>('#metric-select');
  const status = requiredElement<HTMLElement>('#data-status');
  const refreshStatus = requiredElement<HTMLElement>('#refresh-status');
  const navigationLinks = document.querySelectorAll<HTMLAnchorElement>('.site-nav a:not([aria-current="page"])');
  const query = new URLSearchParams(location.search);
  let data: SeasonData | undefined;
  let request: AbortController | undefined;

  function update() {
    if (!data) throw new Error('Rankings data has not been loaded.');
    const metricValue = metric.value;
    if (!isMetric(metricValue)) throw new Error(`Unknown EPA metric: ${metricValue}`);
    const rankings = data.weeks[week.value][metricValue];
    navigationLinks.forEach(link => {
      const url = new URL(link.href);
      for (const [key, value] of [['season', season.value], ['week', week.value], ['metric', metric.value]]) {
        url.searchParams.set(key, value);
      }
      link.href = url.href;
    });
    onChange({ rankings, weeks: data.weeks, week: Number(week.value), season: Number(season.value), metric: metricValue });
  }

  async function loadSeason(preferredWeek?: string | null) {
    request?.abort();
    request = new AbortController();
    const currentRequest = request;
    status.textContent = 'Loading NFL data. The first request may take a minute.';
    status.hidden = false;
    week.disabled = true;
    metric.disabled = true;
    onChange(null);
    try {
      const result = await getJson<SeasonData>(`/api/rankings?season=${encodeURIComponent(season.value)}`, currentRequest.signal);
      if (currentRequest !== request) return;
      const weeks = Object.keys(result.weeks).map(Number).sort((a, b) => b - a);
      if (!weeks.length) throw new Error('No completed weeks are available for this season.');
      data = result;
      week.innerHTML = weeks.map(value => `<option value="${value}">Week ${value}</option>`).join('');
      if (preferredWeek && weeks.some(value => String(value) === preferredWeek)) week.value = preferredWeek;
      week.disabled = false;
      metric.disabled = false;
      status.hidden = true;
      update();
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') return;
      status.textContent = `Unable to load rankings: ${errorMessage(error)} Choose another season or reload to retry.`;
      status.hidden = false;
    }
  }

  season.disabled = true;
  week.disabled = true;
  metric.disabled = true;
  status.hidden = false;
  status.textContent = 'Loading available seasons...';
  try {
    let initialState = await getJson<Status>('/api/status');
    while (!initialState.lastSuccessfulRefresh && !initialState.refreshError) {
      status.textContent = 'Refreshing NFL data for the first time. This may take a few minutes.';
      await new Promise(resolve => setTimeout(resolve, 5000));
      initialState = await getJson<Status>('/api/status');
    }
    if (!initialState.lastSuccessfulRefresh) throw new Error('Initial data refresh failed. Check engine logs.');
    const result = await getJson<{ seasons: number[] }>('/api/seasons');
    if (!result.seasons.length) throw new Error('No seasons are available.');
    season.innerHTML = result.seasons.map(value => `<option value="${value}">${value}</option>`).join('');
    const requestedSeason = query.get('season');
    const requestedMetric = query.get('metric');
    if (requestedSeason && result.seasons.some(value => String(value) === requestedSeason)) season.value = requestedSeason;
    if (requestedMetric && isMetric(requestedMetric)) metric.value = requestedMetric;
    season.disabled = false;
    season.addEventListener('change', () => loadSeason());
    week.addEventListener('change', update);
    metric.addEventListener('change', update);
    await loadSeason(query.get('week'));
  } catch (error) {
    status.textContent = `Unable to load seasons: ${errorMessage(error)} Reload to retry.`;
  }

  async function updateRefreshStatus() {
    try {
      const state = await getJson<Status>('/api/status');
      if (!state.lastSuccessfulRefresh) {
        refreshStatus.textContent = state.refreshError ? 'Data refresh failed. Check engine logs; reload to retry.' : 'Initial data refresh is in progress. Reload when it finishes.';
      } else {
        const refreshed = new Date(state.lastSuccessfulRefresh).toLocaleString();
        const weekLabel = state.latestWeek ? `Latest entered: ${state.latestSeason} Week ${state.latestWeek}.` : '';
        const needsReload = data && state.latestWeek !== null && Number(season.value) === state.latestSeason &&
          state.latestWeek > Math.max(...Object.keys(data.weeks).map(Number));
        refreshStatus.textContent = `${weekLabel} Last updated ${refreshed}.${state.refreshError ? ' Refresh failed; showing stored data. Check engine logs.' : ''}${needsReload ? ' A new week is available; reload to see it.' : ''}`;
      }
    } catch (error) {
      refreshStatus.textContent = `Unable to check data freshness: ${errorMessage(error)}`;
    }

  }
  await updateRefreshStatus();
  setInterval(updateRefreshStatus, 60_000);
}

function isMetric(value: string): value is Metric {
  return value === 'offense' || value === 'defense' || value === 'special' || value === 'combined';
}
