import { escapeHtml } from './components.js';
import type { Game } from './types.js';

export function formatGame(game: Game) {
  if (game.status === 'unavailable') return 'No previous week';
  if (game.status === 'bye') return 'Bye week';
  const result = game.teamScore > game.opponentScore ? 'W' : game.teamScore < game.opponentScore ? 'L' : 'T';
  return `${result} ${game.home ? 'vs' : '@'} ${game.opponent} · ${game.teamScore}–${game.opponentScore}`;
}

export function gameResult(game: Game) {
  return escapeHtml(formatGame(game));
}

export function gameSummary(games: { current: Game; previous: Game }, week: number) {
  return `<div><span>Week ${week}</span><strong>${gameResult(games.current)}</strong></div>
    <div><span>${week > 1 ? `Week ${week - 1}` : 'Previous week'}</span><strong>${gameResult(games.previous)}</strong></div>`;
}
