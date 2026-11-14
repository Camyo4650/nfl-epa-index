import { badge, escapeHtml } from './components.js';
import { setupDataControls } from './api.js';
import { chartPosition, describeMovement } from './movement-chart.js';
import { gameSummary } from './game-details.js';
import { setupMovementExpansion } from './movement-expansion.js';
import { requiredElement } from './dom.js';
import type { Ranking, Selection } from './types.js';

const chartRows = requiredElement<HTMLElement>('#chart-rows');
const comparison = requiredElement<HTMLElement>('#chart-comparison');
const updateControls = setupMovementExpansion(
  chartRows, requiredElement<HTMLButtonElement>('#expand-all'), requiredElement<HTMLButtonElement>('#collapse-all')
);

function chart(team: Ranking) {
  const current = chartPosition(team.rank);
  const previous = team.previousRank === null ? null : chartPosition(team.previousRank);
  let connector = '';
  if (previous !== null && previous !== current) {
    const direction = Math.sign(current - previous);
    const end = current - direction * 13;
    const arrowBase = end - direction * 6;
    const color = team.change !== null && team.change > 0 ? 'chart-up' : 'chart-down';
    connector = `<line class="${color}" x1="${previous}" y1="22" x2="${end}" y2="22" />
      <path class="${color}" d="M ${end} 22 L ${arrowBase} 18 L ${arrowBase} 26 Z" />
      <circle class="chart-previous" cx="${previous}" cy="22" r="5" />`;
  } else if (previous !== null) {
    connector = `<circle class="chart-unchanged" cx="${current}" cy="22" r="15" />`;
  }
  return `<svg class="chart-plot" viewBox="0 0 800 44" role="img" aria-label="${escapeHtml(describeMovement(team))}">
    <line class="chart-baseline" x1="20" y1="22" x2="780" y2="22" />
    ${connector}
    <circle class="chart-current" cx="${current}" cy="22" r="12" />
    <text class="chart-rank" x="${current}" y="22">${team.rank}</text>
  </svg>`;
}

function render(selection: Selection | null) {
  if (!selection) {
    chartRows.innerHTML = '';
    comparison.textContent = '';
    requiredElement<HTMLElement>('#chart-count').textContent = '';
    updateControls();
    return;
  }
  const { rankings, week, metric, season } = selection;
  comparison.textContent = rankings.some(team => team.previousRank !== null)
    ? `${season} ${metric} EPA, Week ${week} compared to Week ${week - 1}.`
    : `Week ${week}. No previous week available.`;
  requiredElement<HTMLElement>('#chart-count').textContent = `${rankings.length} RANKED TEAMS`;
  chartRows.innerHTML = rankings.map((team, index) => `
    <div class="chart-row" role="row">
      <div role="cell">
        <button type="button" class="chart-team chart-team-button" aria-expanded="false" aria-controls="game-details-${index}">${badge(team)}<span><strong>${escapeHtml(team.name)}</strong><small>${escapeHtml(team.conference)} ${escapeHtml(team.division)}</small></span><span class="chart-expand" aria-hidden="true">⌄</span></button>
        <div id="game-details-${index}" class="chart-game-details" hidden>${gameSummary(team.games, week)}</div>
      </div>
      <div role="cell">${chart(team)}</div>
    </div>`).join('');
  updateControls();
}

setupDataControls(render);
