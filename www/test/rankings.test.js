import test from 'node:test';
import assert from 'node:assert/strict';
import { teams, weeklyRankings, weeklyRecords } from '../dist/data.js';
import { filterRankings, formatRecord, getRankings, sortRankings } from '../dist/rankings.js';

test('every sample week ranks all 32 unique NFL teams', () => {
  assert.equal(teams.length, 32);
  assert.equal(new Set(teams.map(team => team.id)).size, 32);
  assert.equal(teams.filter(team => team.conference === 'AFC').length, 16);
  assert.equal(teams.filter(team => team.conference === 'NFC').length, 16);
  for (const week of Object.keys(weeklyRankings)) {
    assert.equal(weeklyRankings[week].length, 32);
    assert.deepEqual(new Set(weeklyRankings[week]), new Set(teams.map(team => team.id)));
    assert.deepEqual(new Set(Object.keys(weeklyRecords[week])), new Set(teams.map(team => team.id)));
    for (const { wins, losses, ties } of Object.values(weeklyRecords[week])) {
      assert.equal(wins + losses + ties, Number(week));
      assert.ok(wins >= 0 && losses >= 0 && ties >= 0);
    }
  }
  for (const team of teams) {
    for (const week of [9, 10]) {
      const current = weeklyRecords[week][team.id];
      const previous = weeklyRecords[week - 1][team.id];
      assert.ok(current.wins >= previous.wins && current.losses >= previous.losses && current.ties >= previous.ties);
    }
  }
});

test('records show ties only when present and preserve ties across weeks', () => {
  assert.equal(formatRecord({ wins: 3, losses: 4, ties: 0 }), '3-4');
  assert.equal(formatRecord({ wins: 3, losses: 4, ties: 1 }), '3-4-1');
  assert.equal(formatRecord({ wins: 3, losses: 4, ties: 2 }), '3-4-2');
  assert.deepEqual(weeklyRecords[8].JAX, { wins: 2, losses: 6, ties: 0 });
  assert.deepEqual(weeklyRecords[9].JAX, { wins: 2, losses: 6, ties: 1 });
  assert.deepEqual(weeklyRecords[10].JAX, { wins: 3, losses: 6, ties: 1 });
});

test('movement compares against the immediate prior week', () => {
  const rankings = getRankings(teams, weeklyRankings, 10, weeklyRecords);
  assert.deepEqual([rankings[0].id, rankings[0].rank, rankings[0].previousRank, rankings[0].change], ['DET', 1, 1, 0]);
  assert.deepEqual([rankings[1].id, rankings[1].previousRank, rankings[1].change], ['BUF', 4, 2]);
  assert.deepEqual([rankings[2].id, rankings[2].previousRank, rankings[2].change], ['KC', 2, -1]);
  assert.equal(getRankings(teams, weeklyRankings, 8, weeklyRecords)[0].change, null);
  assert.deepEqual(rankings[0].record, { wins: 9, losses: 1, ties: 0 });
  assert.deepEqual(getRankings(teams, weeklyRankings, 8, weeklyRecords).find(team => team.id === 'DET').record, { wins: 7, losses: 1, ties: 0 });
});

test('search and conference filters compose without changing rank', () => {
  const rankings = getRankings(teams, weeklyRankings, 10, weeklyRecords);
  assert.equal(filterRankings(rankings, 'AFC', '').length, 16);
  assert.deepEqual(filterRankings(rankings, 'AFC', ' buffalo ').map(team => team.rank), [2]);
  assert.equal(filterRankings(rankings, 'NFC', 'BUF').length, 0);
  assert.deepEqual(filterRankings(rankings, 'ALL', 'lar').map(team => team.id), ['LAR']);
});

test('all columns sort in both directions without mutating rankings', () => {
  const rankings = getRankings(teams, weeklyRankings, 10, weeklyRecords);
  const values = {
    rank: team => team.rank,
    team: team => team.name,
    division: team => `${team.conference} ${team.division}`,
    record: team => (team.record.wins + team.record.ties / 2) / (team.record.wins + team.record.losses + team.record.ties),
    previousRank: team => team.previousRank,
    change: team => team.change
  };
  for (const [column, value] of Object.entries(values)) {
    for (const direction of ['ascending', 'descending']) {
      const sorted = sortRankings(rankings, column, direction);
      for (let i = 1; i < sorted.length; i++) {
        const left = value(sorted[i - 1]);
        const right = value(sorted[i]);
        const comparison = typeof left === 'string' ? left.localeCompare(right) : left - right;
        assert.ok(direction === 'ascending' ? comparison <= 0 : comparison >= 0, `${column} ${direction}`);
        if (comparison === 0) assert.ok(sorted[i - 1].rank < sorted[i].rank);
      }
    }
  }
  assert.deepEqual(rankings.map(team => team.rank), Array.from({ length: 32 }, (_, i) => i + 1));
});

test('record sorting uses winning percentage including ties and keeps unavailable values last', () => {
  const rankings = [
    { rank: 1, record: { wins: 3, losses: 3, ties: 0 }, previousRank: null, change: null },
    { rank: 2, record: { wins: 4, losses: 5, ties: 1 }, previousRank: 4, change: 2 },
    { rank: 3, record: { wins: 0, losses: 0, ties: 0 }, previousRank: 1, change: -2 },
    { rank: 4, record: { wins: 2, losses: 2, ties: 2 }, previousRank: null, change: null }
  ];
  assert.deepEqual(sortRankings(rankings, 'record', 'descending').map(team => team.rank), [1, 4, 2, 3]);
  assert.deepEqual(sortRankings(rankings, 'record', 'ascending').map(team => team.rank), [2, 1, 4, 3]);
  assert.deepEqual(sortRankings(rankings, 'change', 'descending').map(team => team.rank), [2, 3, 1, 4]);
  assert.deepEqual(sortRankings(rankings, 'previousRank', 'ascending').map(team => team.rank), [3, 2, 1, 4]);
});

test('EPA sorting uses numeric values and retains rank order for ties', () => {
  const rows = [{ rank: 1, epa: 0.1 }, { rank: 2, epa: -0.02 }, { rank: 3, epa: 0.1 }];
  assert.deepEqual(sortRankings(rows, 'epa', 'ascending').map(team => team.rank), [2, 1, 3]);
  assert.deepEqual(sortRankings(rows, 'epa', 'descending').map(team => team.rank), [1, 3, 2]);
});

test('strength of schedule rank sorts numerically with unavailable values last', () => {
  const rows = [
    { rank: 1, strengthOfScheduleRank: null },
    { rank: 2, strengthOfScheduleRank: 12 },
    { rank: 3, strengthOfScheduleRank: 1 },
    { rank: 4, strengthOfScheduleRank: 2 }
  ];
  assert.deepEqual(sortRankings(rows, 'strengthOfSchedule', 'ascending').map(team => team.rank), [3, 4, 2, 1]);
  assert.deepEqual(sortRankings(rows, 'strengthOfSchedule', 'descending').map(team => team.rank), [2, 4, 3, 1]);
});

test('season-to-date points columns sort numerically with rank order for ties', () => {
  const rows = [
    { rank: 1, points: { for: 21, allowed: 14, net: 7 } },
    { rank: 2, points: { for: 14, allowed: 21, net: -7 } },
    { rank: 3, points: { for: 21, allowed: 14, net: 7 } }
  ];
  assert.deepEqual(sortRankings(rows, 'pointsFor', 'descending').map(team => team.rank), [1, 3, 2]);
  assert.deepEqual(sortRankings(rows, 'pointsAllowed', 'ascending').map(team => team.rank), [1, 3, 2]);
  assert.deepEqual(sortRankings(rows, 'netPoints', 'ascending').map(team => team.rank), [2, 1, 3]);
});

test('game columns sort by opponent with byes and unavailable weeks last', () => {
  const rows = [
    { rank: 1, games: { current: { status: 'bye' }, previous: { status: 'unavailable' } } },
    { rank: 2, games: { current: { status: 'played', opponent: 'KC' }, previous: { status: 'played', opponent: 'BUF' } } },
    { rank: 3, games: { current: { status: 'played', opponent: 'ARI' }, previous: { status: 'played', opponent: 'DAL' } } },
    { rank: 4, games: { current: { status: 'played', opponent: 'KC' }, previous: { status: 'bye' } } },
    { rank: 5, games: { current: { status: 'unavailable' }, previous: { status: 'played', opponent: 'DAL' } } }
  ];
  assert.deepEqual(sortRankings(rows, 'currentGame', 'ascending').map(team => team.rank), [3, 2, 4, 1, 5]);
  assert.deepEqual(sortRankings(rows, 'currentGame', 'descending').map(team => team.rank), [2, 4, 3, 1, 5]);
  assert.deepEqual(sortRankings(rows, 'previousGame', 'ascending').map(team => team.rank), [2, 3, 5, 1, 4]);
  assert.deepEqual(sortRankings(rows, 'previousGame', 'descending').map(team => team.rank), [3, 5, 2, 1, 4]);
});

test('invalid data is reported rather than silently ignored', () => {
  assert.throws(() => getRankings(teams, weeklyRankings, 42, weeklyRecords), /No rankings available/);
  assert.throws(() => getRankings(teams, { 1: ['UNKNOWN'] }, 1, weeklyRecords), /Unknown team/);
  assert.throws(() => getRankings(teams, { 1: ['KC'] }, 1, weeklyRecords), /No record available/);
  assert.throws(() => sortRankings([], 'invalid', 'ascending'), /Invalid sort/);
});
