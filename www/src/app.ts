import { filterRankings, formatRecord, sortRankings } from './rankings.js';
import { badge, escapeHtml, movement } from './components.js';
import { setupDataControls } from './api.js';
import { gameResult, gameSummary } from './game-details.js';
import { setupRankingsExpansion } from './rankings-expansion.js';
import { requiredElement } from './dom.js';
import type { Selection } from './types.js';

const search = requiredElement<HTMLInputElement>('#team-search');
const leaders = requiredElement<HTMLElement>('#leaders');
const rankingsBody = requiredElement<HTMLElement>('#rankings-body');
const expansion = setupRankingsExpansion(rankingsBody);
const emptyState = requiredElement<HTMLElement>('#empty-state');
const resultCount = requiredElement<HTMLElement>('#result-count');
const comparisonLabel = requiredElement<HTMLElement>('#comparison-label');
const filterButtons = document.querySelectorAll<HTMLButtonElement>('.filter');
const sortButtons = document.querySelectorAll<HTMLButtonElement>('.sort-button');
const columnToggles = document.querySelectorAll<HTMLInputElement>('[data-column-toggle]');
const visibleColumns = new Set([...columnToggles].filter(input => input.checked).map(input => input.dataset.columnToggle));
const columnHidden = (column: string) => visibleColumns.has(column) ? '' : ' hidden';

let conference = 'ALL';
let sortColumn = 'rank';
let sortDirection = 'ascending';
let selection: Selection | null = null;
function render() {
  if (!selection) {
    leaders.innerHTML = '';
    rankingsBody.innerHTML = '';
    resultCount.textContent = '';
    comparisonLabel.textContent = '';
    emptyState.hidden = true;
    return;
  }
  const { rankings, week, metric } = selection;
  const filtered = sortRankings(filterRankings(rankings, conference, search.value), sortColumn, sortDirection);

  sortButtons.forEach(button => {
    const active = button.dataset.sort === sortColumn;
    const header = button.parentElement;
    if (!header) throw new Error('Sort button has no header.');
    if (active) header.setAttribute('aria-sort', sortDirection);
    else header.removeAttribute('aria-sort');
    requiredElement<HTMLElement>('[aria-hidden="true"]', button).textContent = active ? (sortDirection === 'ascending' ? '↑' : '↓') : '↕';
  });
  requiredElement<HTMLElement>('[data-game-week="current"]').textContent = `WEEK ${week} GAME`;
  requiredElement<HTMLElement>('[data-game-week="previous"]').textContent = week > 1 ? `WEEK ${week - 1} GAME` : 'PREVIOUS WEEK';

  comparisonLabel.textContent = rankings.some(team => team.previousRank !== null) ? `Compared to Week ${week - 1}.` : 'No previous week available.';
  requiredElement<HTMLElement>('#metric-label').textContent = {
    combined: 'Combined EPA/play',
    offense: 'Offensive EPA/play',
    defense: 'Defensive EPA/play allowed',
    special: 'Net special-teams EPA/play'
  }[metric];
  leaders.innerHTML = rankings.slice(0, 3).map(team => `
    <article class="leader-card">
      <div class="leader-card-top"><span class="leader-number">0${team.rank} <span>/ 32</span></span><span class="leader-movement">${movement(team)}</span></div>
      <div class="leader-team">${badge(team, true)}<div><span class="leader-conference">${escapeHtml(team.conference)} ${escapeHtml(team.division.toUpperCase())}</span><h3>${escapeHtml(team.name)}</h3></div></div>
      <div class="leader-bottom"><span>EPA RANK</span><strong>#${team.rank}</strong><span class="leader-arrow" aria-hidden="true">↗</span></div>
    </article>`).join('');

  rankingsBody.innerHTML = filtered.map((team, index) => `
    <tr class="rankings-row" data-team="${escapeHtml(team.id)}">
      <td class="rank-cell"${columnHidden('rank')}><span>${String(index + 1).padStart(2, '0')}</span></td>
      <td><button type="button" class="team-cell rankings-team-button" aria-expanded="${expansion.isExpanded(team.id)}" aria-controls="rankings-game-details-${index}">${badge(team)}<span><strong>${escapeHtml(team.name)}</strong><small>${escapeHtml(team.id)}</small></span><span class="rankings-expand" aria-hidden="true">⌄</span></button>
        <div id="rankings-game-details-${index}" class="rankings-game-details"${expansion.isExpanded(team.id) ? '' : ' hidden'}>${gameSummary(team.games, week)}</div></td>
      <td class="division-cell"${columnHidden('division')}><span>${escapeHtml(team.conference)}</span> ${escapeHtml(team.division)}</td>
      <td class="record-cell"${columnHidden('record')}>${formatRecord(team.record)}</td>
      <td class="game-cell"${columnHidden('currentGame')}>${gameResult(team.games.current)}</td>
      <td class="game-cell"${columnHidden('previousGame')}>${gameResult(team.games.previous)}</td>
      <td${columnHidden('pointsFor')}>${team.points.for}</td>
      <td${columnHidden('pointsAllowed')}>${team.points.allowed}</td>
      <td${columnHidden('netPoints')}>${team.points.net > 0 ? '+' : ''}${team.points.net}</td>
      <td class="epa-cell"${columnHidden('epa')}>${team.epa.toFixed(3)}</td>
      <td class="epa-cell"${columnHidden('strengthOfSchedule')}>${team.strengthOfScheduleRank === null ? '—' : `#${team.strengthOfScheduleRank}`}</td>
      <td class="previous-cell"${columnHidden('previousRank')}>${team.previousRank === null ? '—' : String(team.previousRank).padStart(2, '0')}</td>
      <td${columnHidden('change')}>${movement(team)}</td>
    </tr>`).join('');
  emptyState.hidden = filtered.length !== 0;
  resultCount.textContent = `SHOWING ${filtered.length} OF ${rankings.length} TEAMS`;
}

filterButtons.forEach(button => button.addEventListener('click', () => {
  const selected = button.dataset.conference;
  if (!selected) throw new Error('Conference filter is missing its value.');
  conference = selected;
  filterButtons.forEach(filter => {
    const active = filter === button;
    filter.classList.toggle('active', active);
    filter.setAttribute('aria-pressed', String(active));
  });
  render();
}));
sortButtons.forEach(button => button.addEventListener('click', () => {
  const column = button.dataset.sort;
  if (!column) throw new Error('Sort button is missing its column.');
  if (sortColumn === column) {
    sortDirection = sortDirection === 'ascending' ? 'descending' : 'ascending';
  } else {
    sortColumn = column;
    sortDirection = ['record', 'change', 'epa', 'pointsFor', 'pointsAllowed', 'netPoints'].includes(column) ? 'descending' : 'ascending';
  }
  render();
}));
columnToggles.forEach(input => input.addEventListener('change', () => {
  const column = input.dataset.columnToggle;
  if (!column) throw new Error('Column toggle is missing its column.');
  if (input.checked) visibleColumns.add(column);
  else visibleColumns.delete(column);
  requiredElement<HTMLElement>(`th[data-column="${column}"]`).hidden = !input.checked;
  if (!input.checked && sortColumn === column) {
    sortColumn = 'rank';
    sortDirection = 'ascending';
  }
  render();
}));
setupDataControls(value => {
  selection = value;
  expansion.reset();
  render();
});
search.addEventListener('input', render);
document.addEventListener('keydown', event => {
  if (event.key === '/' && !event.metaKey && !event.ctrlKey && !event.altKey && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName ?? '')) {
    event.preventDefault();
    search.focus();
  }
});
