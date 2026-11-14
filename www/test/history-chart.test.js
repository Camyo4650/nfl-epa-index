import test from 'node:test';
import assert from 'node:assert/strict';
import { groupHistoryTeams, historyPosition, historyRankAxis, historySegments, rankingHistory } from '../dist/history-chart.js';

test('history orders weeks and keeps per-team ranks for the chosen metric', () => {
  const data = {
    3: { combined: [{ id: 'B', name: 'Bravo', rank: 1 }, { id: 'A', name: 'Alpha', rank: 2 }] },
    1: { combined: [{ id: 'A', name: 'Alpha', rank: 1 }] },
    2: { combined: [{ id: 'B', name: 'Bravo', rank: 1 }, { id: 'A', name: 'Alpha', rank: 2 }] }
  };
  const result = rankingHistory(data, 'combined');
  assert.deepEqual(result.weeks, [1, 2, 3]);
  assert.deepEqual(result.teams.map(item => item.team.id), ['A', 'B']);
  assert.deepEqual([...result.teams[0].ranks], [[1, 1], [2, 2], [3, 2]]);
  assert.deepEqual([...result.teams[1].ranks], [[2, 1], [3, 1]]);
});

test('missing team or missing calendar week breaks the line', () => {
  const ranks = new Map([[1, 4], [3, 2], [4, 1], [6, 3]]);
  assert.deepEqual(historySegments([1, 2, 3, 4, 6], ranks), [
    [{ week: 1, rank: 4 }],
    [{ week: 3, rank: 2 }, { week: 4, rank: 1 }],
    [{ week: 6, rank: 3 }]
  ]);
});

test('rank 1 is at the top and weeks are spaced on a common scale', () => {
  assert.deepEqual(historyPosition(1, 1, 1, 3, 820, 680), { x: 48, y: 22 });
  assert.deepEqual(historyPosition(3, 32, 1, 3, 820, 680), { x: 796, y: 646 });
  assert.equal(historyPosition(2, 8, 1, 3, 820, 680).x, 422);
  assert.equal(historyPosition(1, 1, 1, 1, 820, 680).x, 410);
});

test('rank axis fits selected teams across weeks with bounded padding and integer ticks', () => {
  const team = (...ranks) => ({ ranks: new Map(ranks.map((rank, index) => [index + 1, rank])) });
  assert.deepEqual(historyRankAxis([]), { min: 1, max: 32, ticks: [1, 8, 16, 24, 32] });
  assert.deepEqual(historyRankAxis([team(5, 9), team(3, 8)]), { min: 2, max: 10, ticks: [2, 4, 6, 8, 10] });
  assert.deepEqual(historyRankAxis([team(1)]), { min: 1, max: 2, ticks: [1, 2] });
  assert.deepEqual(historyRankAxis([team(32)]), { min: 31, max: 32, ticks: [31, 32] });
  assert.deepEqual(historyRankAxis([team(17)]), { min: 16, max: 18, ticks: [16, 17, 18] });
  const axis = historyRankAxis([team(5, 9), team(3, 8)]);
  assert.equal(historyPosition(1, 2, 1, 3, 820, 680, axis).y, 22);
  assert.equal(historyPosition(1, 10, 1, 3, 820, 680, axis).y, 646);
  assert.equal(historyPosition(1, 6, 1, 3, 820, 680, axis).y, 334);
});

test('invalid rankings fail explicitly', () => {
  assert.throws(() => rankingHistory({ 1: { combined: [{ id: 'A', rank: 33 }] } }, 'combined'), /Invalid rank/);
});

test('teams are grouped by conference and division, then sorted by name', () => {
  const teams = [
    { team: { name: 'Jets', conference: 'AFC', division: 'East' } },
    { team: { name: 'Giants', conference: 'NFC', division: 'East' } },
    { team: { name: 'Bills', conference: 'AFC', division: 'East' } },
    { team: { name: 'Bengals', conference: 'AFC', division: 'North' } }
  ];
  const groups = groupHistoryTeams(teams);
  assert.deepEqual(groups.map(group => group.label), ['AFC East', 'AFC North', 'NFC East']);
  assert.deepEqual(groups[0].teams.map(entry => entry.team.name), ['Bills', 'Jets']);
  assert.deepEqual(teams.map(entry => entry.team.name), ['Jets', 'Giants', 'Bills', 'Bengals']);
});
