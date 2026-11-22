// Rank 1 is at the right so improvement always points right.
import { escapeHtml } from './components.js';
import type { Ranking } from './types.js';

export function chartPosition(rank: number) {
  if (!Number.isInteger(rank) || rank < 1 || rank > 32) {
    throw new Error(`Invalid chart rank: ${rank}.`);
  }
  return 20 + (32 - rank) * 760 / 31;
}

export function describeMovement(team: Pick<Ranking, 'name' | 'rank' | 'previousRank' | 'change'>) {
  if (team.previousRank === null) return `${team.name}: current rank ${team.rank}; no previous ranking available.`;
  if (team.change === 0) return `${team.name}: unchanged at rank ${team.rank}.`;
  if (team.change === null) throw new Error(`Missing movement for ${team.name}.`);
  const direction = team.change > 0 ? 'up' : 'down';
  const places = Math.abs(team.change);
  return `${team.name}: ${direction} ${places} ${places === 1 ? 'place' : 'places'}, from rank ${team.previousRank} to rank ${team.rank}.`;
}

export function movementChart(team: Ranking) {
  const current = chartPosition(team.rank);
  const previous = team.previousRank === null ? null : chartPosition(team.previousRank);
  const color = previous === null || previous === current ? 'chart-neutral'
    : team.change !== null && team.change > 0 ? 'chart-up' : 'chart-down';
  let connector = '';
  if (previous !== null && previous !== current) {
    const direction = Math.sign(current - previous);
    const end = current - direction * 13;
    const arrowBase = end - direction * 6;
    connector = `<line class="${color}" x1="${previous}" y1="22" x2="${end}" y2="22" />
      <path class="${color}" d="M ${end} 22 L ${arrowBase} 18 L ${arrowBase} 26 Z" />
      <circle class="chart-previous ${color}" cx="${previous}" cy="22" r="8" />
      <text class="chart-rank chart-rank-previous ${color}" x="${previous}" y="22">${team.previousRank}</text>`;
  } else if (previous !== null) {
    connector = `<circle class="chart-unchanged" cx="${current}" cy="22" r="15" />`;
  }
  return `<svg class="chart-plot" viewBox="0 0 800 44" role="img" aria-label="${escapeHtml(describeMovement(team))}">
    <line class="chart-baseline" x1="20" y1="22" x2="780" y2="22" />
    ${connector}
    <circle class="chart-current ${color}" cx="${current}" cy="22" r="12" />
    <text class="chart-rank" x="${current}" y="22">${team.rank}</text>
  </svg>`;
}
