import { escapeHtml } from './components.js';
import { setupDataControls } from './api.js';
import { groupHistoryTeams, historyPosition, historyRankAxis, historySegments, rankingHistory } from './history-chart.js';
import type { HistoryMode } from './history-chart.js';
import { setupPointTooltip } from './history-point-tooltip.js';
import { requiredElement } from './dom.js';
import type { Selection, Team } from './types.js';

const chart = requiredElement<HTMLElement>('#history-chart');
const teamList = requiredElement<HTMLFieldSetElement>('#history-teams');
const table = requiredElement<HTMLElement>('#history-table');
const empty = requiredElement<HTMLElement>('#history-empty');
const count = requiredElement<HTMLElement>('#history-count');
const comparison = requiredElement<HTMLElement>('#history-comparison');
const selectAll = requiredElement<HTMLButtonElement>('#select-all');
const clearAll = requiredElement<HTMLButtonElement>('#clear-all');
const highlightStatus = requiredElement<HTMLElement>('#highlight-status');
const clearHighlight = requiredElement<HTMLButtonElement>('#clear-highlight');
const modeSelect = requiredElement<HTMLSelectElement>('#history-mode');
const hidePointTooltip = setupPointTooltip(chart, requiredElement<HTMLElement>('#history-point-tooltip'));
let selection: Selection | null = null;
let history: ReturnType<typeof rankingHistory> | null = null;
let chosen = new Set<string>();
let activeSeason: number | null = null;
let highlightedTeam: string | null = null;
let mode: HistoryMode = 'overall';

function color(team: Team) {
  return /^#[0-9a-f]{6}$/i.test(team.color) ? team.color : '#274c37';
}

function render(rebuildTeams = true) {
  hidePointTooltip();
  if (!selection) {
    chart.innerHTML = '';
    table.innerHTML = '';
    teamList.innerHTML = '<legend>Teams</legend>';
    teamList.disabled = true;
    selectAll.disabled = true;
    clearAll.disabled = true;
    empty.hidden = true;
    count.textContent = '';
    comparison.textContent = '';
    highlightStatus.textContent = '';
    clearHighlight.disabled = true;
    modeSelect.disabled = true;
    return;
  }
  if (!history) throw new Error('Ranking history has not been loaded.');
  const { weeks, teams } = history;
  const visible = teams.filter(({ team }) => chosen.has(team.id));
  const width = Math.max(820, (weeks[weeks.length - 1] - weeks[0]) * 55 + 72);
  const height = 680;
  const axis = historyRankAxis(visible, mode === 'overall' ? 32 : 16);
  const point = (week: number, rank: number) => historyPosition(week, rank, weeks[0], weeks[weeks.length - 1], width, height, axis);
  const grid = axis.ticks.map(rank => {
    const y = point(weeks[0], rank).y;
    return `<line x1="48" y1="${y}" x2="${width - 24}" y2="${y}" class="history-grid"/><text x="35" y="${y}" text-anchor="end" dominant-baseline="middle">${rank}</text>`;
  }).join('');
  const ticks = weeks.map(week => {
    const x = point(week, 1).x;
    return `<text x="${x}" y="${height - 12}" text-anchor="middle">${week}</text>`;
  }).join('');
  const selectedX = point(selection.week, 1).x;
  const series = visible.map(({ team, ranks }) => {
    const paths = historySegments(weeks, ranks).map(segment => {
      const points = segment.map(({ week, rank }) => point(week, rank));
      const path = points.map(({ x, y }, index) => `${index ? 'L' : 'M'} ${x} ${y}`).join(' ');
      return `<path d="${path}" fill="none" stroke="${color(team)}" stroke-width="2.5" pointer-events="none" />
        <path d="${path}" class="history-line-hit" data-history-select />`;
    }).join('');
    const dots = weeks.filter(week => ranks.has(week)).map(week => {
      const rank = ranks.get(week)!;
      const { x, y } = point(week, rank);
      return `<circle cx="${x}" cy="${y}" r="3" fill="${color(team)}" pointer-events="none" />
        <circle cx="${x}" cy="${y}" r="8" class="history-point-hit" data-history-select data-name="${escapeHtml(team.name)}" data-week="${week}" data-rank="${rank}" />`;
    }).join('');
    return { paths: `<g class="history-series" data-team="${escapeHtml(team.id)}">${paths}</g>`,
      dots: `<g class="history-series" data-team="${escapeHtml(team.id)}">${dots}</g>` };
  });
  chart.innerHTML = `<svg class="history-svg" style="width:${width}px" viewBox="0 0 ${width} ${height}" role="img" aria-label="Weekly EPA ranking history for ${visible.length} selected teams. Rank axis runs from ${axis.min} at the top to ${axis.max} at the bottom. Use the data table below for exact ranks.">
    ${grid}<line class="history-current" x1="${selectedX}" y1="22" x2="${selectedX}" y2="${height - 34}"/><text x="${selectedX}" y="12" text-anchor="middle">W${selection.week}</text>${series.map(item => item.paths).join('')}${series.map(item => item.dots).join('')}${ticks}
  </svg>`;
  if (rebuildTeams) {
    teamList.innerHTML = '<legend>Teams</legend>' + groupHistoryTeams(teams).map(group => `
      <div class="history-division" role="group" aria-label="${escapeHtml(group.label)}">
        <h3>${escapeHtml(group.label)}</h3>
        ${group.teams.map(({ team }) => `
          <div class="history-team" data-team="${escapeHtml(team.id)}">
            <label><input type="checkbox" value="${escapeHtml(team.id)}"${chosen.has(team.id) ? ' checked' : ''}>
              <span class="history-swatch" style="--team-color:${color(team)}" aria-hidden="true"></span><span>${escapeHtml(team.name)}</span></label>
            <button type="button" class="history-highlight-button" aria-label="Highlight ${escapeHtml(team.name)}" aria-pressed="false"${chosen.has(team.id) ? '' : ' hidden'}>Focus</button>
          </div>`).join('')}
      </div>`).join('');
  }
  teamList.disabled = false;
  modeSelect.disabled = false;
  selectAll.disabled = visible.length === teams.length;
  clearAll.disabled = visible.length === 0;
  empty.hidden = visible.length !== 0;
  count.textContent = `${visible.length} OF ${teams.length} TEAMS SELECTED`;
  const scope = mode === 'overall' ? 'league-wide' : `${mode} conference`;
  comparison.textContent = `${selection.season} ${selection.metric} EPA ${scope} rankings, all available weeks.`;
  table.innerHTML = `<table><caption class="sr-only">${selection.season} ${escapeHtml(selection.metric)} EPA ${scope} rankings by week</caption><thead><tr><th scope="col">TEAM</th>${weeks.map(week => `<th scope="col">W${week}</th>`).join('')}</tr></thead><tbody>${visible.map(({ team, ranks }) => `<tr><th scope="row">${escapeHtml(team.name)}</th>${weeks.map(week => `<td>${ranks.has(week) ? ranks.get(week) : '—'}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  if (!visible.some(({ team }) => team.id === highlightedTeam)) highlightedTeam = null;
  updateHighlight();
}

function updateHighlight() {
  if (!history) throw new Error('Ranking history has not been loaded.');
  const svg = requiredElement<SVGElement>('.history-svg', chart);
  const series = [...svg.querySelectorAll<SVGElement>('.history-series')];
  svg.classList.toggle('has-highlight', highlightedTeam !== null);
  series.forEach(item => item.classList.toggle('highlighted', item.dataset.team === highlightedTeam));
  teamList.querySelectorAll<HTMLElement>('.history-team').forEach(item => {
    const button = requiredElement<HTMLButtonElement>('.history-highlight-button', item);
    button.hidden = !item.dataset.team || !chosen.has(item.dataset.team);
    button.setAttribute('aria-pressed', String(item.dataset.team === highlightedTeam));
  });
  const team = history.teams.find(item => item.team.id === highlightedTeam);
  highlightStatus.textContent = team ? `Highlighted: ${team.team.name}` : 'No team highlighted';
  clearHighlight.disabled = !team;
}

function toggleHighlight(id: string) {
  highlightedTeam = highlightedTeam === id ? null : id;
  updateHighlight();
}

chart.addEventListener('click', event => {
  const target = event.target instanceof Element ? event.target.closest('[data-history-select]') : null;
  const id = target?.closest<SVGElement>('.history-series')?.dataset.team;
  if (id) toggleHighlight(id);
});
teamList.addEventListener('click', event => {
  const button = event.target instanceof Element ? event.target.closest('.history-highlight-button') : null;
  const id = button?.closest<HTMLElement>('.history-team')?.dataset.team;
  if (id) toggleHighlight(id);
});
clearHighlight.addEventListener('click', () => {
  highlightedTeam = null;
  updateHighlight();
});
teamList.addEventListener('change', event => {
  const input = event.target;
  if (!(input instanceof HTMLInputElement) || !input.matches('input[type="checkbox"]')) return;
  if (input.checked) chosen.add(input.value);
  else chosen.delete(input.value);
  render(false);
});
selectAll.addEventListener('click', () => {
  if (!history) return;
  chosen = new Set(history.teams.map(({ team }) => team.id));
  render();
});
clearAll.addEventListener('click', () => {
  chosen.clear();
  render();
});

modeSelect.addEventListener('change', () => {
  if (!selection || (modeSelect.value !== 'overall' && modeSelect.value !== 'NFC' && modeSelect.value !== 'AFC')) return;
  mode = modeSelect.value;
  history = rankingHistory(selection.weeks, selection.metric, mode);
  chosen = new Set(history.teams.map(({ team }) => team.id));
  highlightedTeam = null;
  render();
});

setupDataControls(value => {
  selection = value;
  if (value) {
    history = rankingHistory(value.weeks, value.metric, mode);
    if (value.season !== activeSeason) {
      chosen = new Set(history.teams.map(({ team }) => team.id));
      activeSeason = value.season;
      highlightedTeam = null;
    }
  }
  render();
});
