import test from 'node:test';
import assert from 'node:assert/strict';
import { chartPosition, describeMovement } from '../dist/movement-chart.js';

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
