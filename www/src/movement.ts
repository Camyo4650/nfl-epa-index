import { badge, escapeHtml } from './components.js';
import { setupDataControls } from './api.js';
import { movementChart } from './movement-chart.js';
import { gameSummary } from './game-details.js';
import { setupMovementExpansion } from './movement-expansion.js';
import { requiredElement } from './dom.js';
import type { Ranking, Selection } from './types.js';

const chartRows = requiredElement<HTMLElement>('#chart-rows');
const comparison = requiredElement<HTMLElement>('#chart-comparison');
const updateControls = setupMovementExpansion(
  chartRows, requiredElement<HTMLButtonElement>('#expand-all'), requiredElement<HTMLButtonElement>('#collapse-all')
);

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
      <div role="cell">${movementChart(team)}</div>
    </div>`).join('');
  updateControls();
}

setupDataControls(render);
