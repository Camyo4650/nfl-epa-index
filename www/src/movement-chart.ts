// Rank 1 is at the right so improvement always points right.
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
