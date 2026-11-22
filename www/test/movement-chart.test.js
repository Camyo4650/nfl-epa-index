import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.document = { addEventListener() {} };
const { chartPosition, describeMovement, movementChart } = await import('../dist/movement-chart.js');

test('chart positions improve to the right on a consistent 32-rank scale', () => {
  assert.equal(chartPosition(32), 20);
  assert.equal(chartPosition(1), 780);
  for (let rank = 1; rank < 32; rank++) {
    assert.ok(chartPosition(rank) > chartPosition(rank + 1));
  }
  assert.throws(() => chartPosition(0), /Invalid chart rank/);
  assert.throws(() => chartPosition(33), /Invalid chart rank/);
});

test('chart descriptions distinguish movement, no change, and unavailable previous ranks', () => {
  assert.match(describeMovement({ name: 'Bills', rank: 2, previousRank: 4, change: 2 }), /up 2 places, from rank 4 to rank 2/);
  assert.match(describeMovement({ name: 'Chiefs', rank: 3, previousRank: 2, change: -1 }), /down 1 place, from rank 2 to rank 3/);
  assert.match(describeMovement({ name: 'Lions', rank: 1, previousRank: 1, change: 0 }), /unchanged at rank 1/);
  assert.match(describeMovement({ name: 'Lions', rank: 1, previousRank: null, change: null }), /no previous ranking available/);
});

test('movement chart labels both ranks and colors the current marker by movement', () => {
  const team = {
    name: 'Bills', id: 'BUF', conference: 'AFC', division: 'East', color: '',
    rank: 2, previousRank: 4, change: 2, record: { wins: 0, losses: 0, ties: 0 },
    epa: 0, strengthOfScheduleRank: null,
    points: { for: 0, allowed: 0, net: 0 },
    games: { current: { status: 'unavailable' }, previous: { status: 'unavailable' } }
  };
  const chart = movementChart(team);
  assert.match(chart, /class="chart-previous chart-up"[^>]*r="8"/);
  assert.match(chart, /class="chart-current chart-up"[^>]*r="12"/);
  assert.match(chart, /class="chart-rank chart-rank-previous chart-up"[^>]*>4<\/text>/);
  assert.match(chart, /class="chart-rank"[^>]*>2<\/text>/);
  const declined = movementChart({ ...team, rank: 4, previousRank: 2, change: -2 });
  assert.match(declined, /class="chart-previous chart-down"/);
  assert.match(declined, /class="chart-current chart-down"/);
  assert.match(declined, /class="chart-rank chart-rank-previous chart-down"[^>]*>2<\/text>/);
  const unchanged = movementChart({ ...team, previousRank: 2, change: 0 });
  assert.match(unchanged, /class="chart-unchanged"/);
  assert.match(unchanged, /class="chart-current chart-neutral"/);
  const unavailable = movementChart({ ...team, previousRank: null, change: null });
  assert.doesNotMatch(unavailable, /class="chart-previous/);
  assert.doesNotMatch(unavailable, /class="chart-unchanged/);
  assert.match(unavailable, /class="chart-current chart-neutral"/);
});
