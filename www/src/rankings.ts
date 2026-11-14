/**
 * Turn ordered weekly snapshots into display-ready rankings.
 * A positive change means a team moved up; null means no prior ranking exists.
 */
export function getRankings<T extends Team>(teams: T[], weeklyRankings: Record<number, string[]>, week: number, weeklyRecords: Record<number, Record<string, RecordData>>) {
  const current = weeklyRankings[week];
  if (!current) throw new Error(`No rankings available for week ${week}.`);

  const teamsById = new Map(teams.map(team => [team.id, team]));
  const previous = weeklyRankings[Number(week) - 1];
  const previousRanks = new Map(previous?.map((id, index) => [id, index + 1]) ?? []);

  return current.map((id, index) => {
    const team = teamsById.get(id);
    if (!team) throw new Error(`Unknown team in week ${week}: ${id}.`);
    const record = weeklyRecords[week]?.[id];
    if (!record) throw new Error(`No record available for ${id} in week ${week}.`);
    const rank = index + 1;
    const previousRank = previousRanks.get(id) ?? null;
    return { ...team, record, rank, previousRank, change: previousRank === null ? null : previousRank - rank };
  });
}

export function formatRecord({ wins, losses, ties }: RecordData) {
  return `${wins}-${losses}${ties > 0 ? `-${ties}` : ''}`;
}

export function sortRankings(rankings: Ranking[], column: string, direction: string) {
  const values: Record<string, (team: Ranking) => string | number | null> = {
    rank: team => team.rank,
    team: team => team.name,
    division: team => `${team.conference} ${team.division}`,
    record: team => {
      const { wins, losses, ties } = team.record;
      const games = wins + losses + ties;
      return games === 0 ? null : (wins + ties / 2) / games;
    },
    epa: team => team.epa,
    strengthOfSchedule: team => team.strengthOfScheduleRank,
    pointsFor: team => team.points.for,
    pointsAllowed: team => team.points.allowed,
    netPoints: team => team.points.net,
    currentGame: team => team.games.current.status === 'played' ? team.games.current.opponent : null,
    previousGame: team => team.games.previous.status === 'played' ? team.games.previous.opponent : null,
    previousRank: team => team.previousRank,
    change: team => team.change
  };
  const getValue = values[column];
  if (!getValue || !['ascending', 'descending'].includes(direction)) {
    throw new Error(`Invalid sort: ${column} ${direction}.`);
  }
  const multiplier = direction === 'ascending' ? 1 : -1;
  return [...rankings].sort((a, b) => {
    const left = getValue(a);
    const right = getValue(b);
    if (left === null || right === null) {
      return left === right ? a.rank - b.rank : left === null ? 1 : -1;
    }
    if (typeof left !== typeof right) throw new Error(`Inconsistent values for sort: ${column}.`);
    const comparison = typeof left === 'string' && typeof right === 'string' ? left.localeCompare(right)
      : typeof left === 'number' && typeof right === 'number' ? left - right : 0;
    return comparison * multiplier || a.rank - b.rank;
  });
}

export function filterRankings(rankings: Ranking[], conference: string, search: string) {
  const query = search.trim().toLowerCase();
  return rankings.filter(team =>
    (conference === 'ALL' || team.conference === conference) &&
    `${team.name} ${team.id}`.toLowerCase().includes(query)
  );
}
import type { Ranking, RecordData, Team } from './types.js';
