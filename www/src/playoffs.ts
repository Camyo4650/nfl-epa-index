import { getJson, setupDataControls } from './api.js';
import { errorMessage, requiredElement } from './dom.js';
import { renderPlayoffTeams } from './playoff-cards.js';
import { parsePlayoffResponse, pollPlayoffPicture } from './playoff-poll.js';
import type { PlayoffTeam } from './playoff-cards.js';

interface PlayoffPicture {
  season: number;
  week: number;
  statusSource: 'postseason' | 'record_bounds';
  conferences: { AFC: PlayoffTeam[]; NFC: PlayoffTeam[] };
}

function isPlayoffPicture(value: unknown): value is PlayoffPicture {
  if (typeof value !== 'object' || value === null ||
      !('season' in value) || typeof value.season !== 'number' ||
      !('week' in value) || typeof value.week !== 'number' ||
      !('statusSource' in value) || (value.statusSource !== 'postseason' && value.statusSource !== 'record_bounds') ||
      !('conferences' in value) || typeof value.conferences !== 'object' || value.conferences === null) return false;
  return 'AFC' in value.conferences && Array.isArray(value.conferences.AFC) &&
    'NFC' in value.conferences && Array.isArray(value.conferences.NFC);
}

const afc = requiredElement<HTMLElement>('#afc-teams');
const nfc = requiredElement<HTMLElement>('#nfc-teams');
const status = requiredElement<HTMLElement>('#playoff-status');
const label = requiredElement<HTMLElement>('#picture-week');
const source = requiredElement<HTMLElement>('#playoff-source');
let request: AbortController | undefined;

setupDataControls(async selection => {
  request?.abort();
  afc.innerHTML = '';
  nfc.innerHTML = '';
  label.textContent = '';
  source.textContent = '';
  if (!selection) {
    status.hidden = true;
    return;
  }
  const url = new URL(location.href);
  url.searchParams.set('season', String(selection.season));
  url.searchParams.set('week', String(selection.week));
  url.searchParams.set('metric', selection.metric);
  history.replaceState(history.state, '', url);
  const current = new AbortController();
  request = current;
  status.textContent = 'Loading playoff picture...';
  status.hidden = false;
  try {
    const result = await pollPlayoffPicture<PlayoffPicture>(
      async () => {
        const response = await getJson<unknown>(
          `/api/playoffs?season=${selection.season}&week=${selection.week}`, current.signal);
        return parsePlayoffResponse(response, isPlayoffPicture);
      },
      current.signal,
      progress => {
        status.textContent = progress
          ? `Simulating playoff picture: ${Math.floor(100 * progress.completed / progress.total)}% (${progress.completed.toLocaleString()} of ${progress.total.toLocaleString()} simulations).`
          : 'Checking for a cached playoff picture or waiting for a simulation to start.';
      });
    if (request !== current) return;
    const finalResults = result.statusSource === 'postseason';
    afc.innerHTML = renderPlayoffTeams(result.conferences.AFC, finalResults);
    nfc.innerHTML = renderPlayoffTeams(result.conferences.NFC, finalResults);
    source.textContent = finalResults
      ? 'Final playoff qualifications and division winners are based on the postseason schedule. Their 0% or 100% values are final results; ordering within groups remains provisional.'
      : 'Clinched and eliminated labels are based on conservative record bounds. Where these cannot resolve tiebreakers, labels are omitted; 0% or 100% estimates alone are not proof.';
    label.textContent = `${result.season} season · through Week ${result.week}`;
    status.hidden = true;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') return;
    if (request !== current) return;
    status.textContent = `Unable to load playoff picture: ${errorMessage(error)} Choose another week or reload to retry.`;
  }
});
