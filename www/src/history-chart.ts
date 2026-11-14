import type { HistoryTeam, Metric, WeeklySnapshots } from './types.js';

export function rankingHistory(weeklySnapshots: WeeklySnapshots, metric: Metric) {
  const weeks = Object.keys(weeklySnapshots).map(Number).sort((a, b) => a - b);
  const teams = new Map<string, HistoryTeam>();
  for (const week of weeks) {
    for (const team of weeklySnapshots[week][metric]) {
      if (!Number.isInteger(team.rank) || team.rank < 1 || team.rank > 32) {
        throw new Error(`Invalid rank for ${team.id} in week ${week}: ${team.rank}.`);
      }
      if (!teams.has(team.id)) teams.set(team.id, { team, ranks: new Map() });
      const entry = teams.get(team.id)!;
      entry.team = team;
      entry.ranks.set(week, team.rank);
    }
  }
  return { weeks, teams: [...teams.values()].sort((a, b) => a.team.name.localeCompare(b.team.name)) };
}

export function historySegments(weeks: number[], ranks: Map<number, number>) {
  const segments: { week: number; rank: number }[][] = [];
  let segment: { week: number; rank: number }[] = [];
  for (const week of weeks) {
    if (!ranks.has(week)) {
      if (segment.length) segments.push(segment);
      segment = [];
      continue;
    }
    if (segment.length && week !== segment[segment.length - 1].week + 1) {
      segments.push(segment);
      segment = [];
    }
    segment.push({ week, rank: ranks.get(week)! });
  }
  if (segment.length) segments.push(segment);
  return segments;
}

export function historyRankAxis(teams: HistoryTeam[]) {
  const ranks = teams.flatMap(({ ranks }) => [...ranks.values()]);
  if (!ranks.length) return { min: 1, max: 32, ticks: [1, 8, 16, 24, 32] };

  const min = Math.max(1, Math.min(...ranks) - 1);
  const max = Math.min(32, Math.max(...ranks) + 1);
  const step = [1, 2, 5, 10].find(value => (max - min) / value <= 5) ?? 10;
  const ticks = [min];
  for (let rank = Math.ceil((min + 1) / step) * step; rank < max; rank += step) {
    ticks.push(rank);
  }
  ticks.push(max);
  return { min, max, ticks };
}

export function historyPosition(week: number, rank: number, firstWeek: number, lastWeek: number, width: number, height: number, axis = { min: 1, max: 32 }) {
  return {
    x: firstWeek === lastWeek ? width / 2 : 48 + (week - firstWeek) * (width - 72) / (lastWeek - firstWeek),
    y: 22 + (rank - axis.min) * (height - 56) / (axis.max - axis.min)
  };
}

export function groupHistoryTeams(teams: HistoryTeam[]) {
  const groups = new Map<string, HistoryTeam[]>();
  for (const entry of teams) {
    const { conference, division } = entry.team;
    const label = `${conference} ${division}`;
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label)!.push(entry);
  }
  return [...groups].sort(([left], [right]) => left.localeCompare(right)).map(([label, entries]) => ({
    label,
    teams: entries.slice().sort((a, b) => a.team.name.localeCompare(b.team.name))
  }));
}
