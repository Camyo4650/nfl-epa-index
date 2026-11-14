import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.document = { addEventListener() {} };
const { formatGame, gameResult, gameSummary } = await import('../dist/game-details.js');

test('formats game results from the selected team perspective', () => {
  assert.equal(formatGame({ status: 'played', home: true, opponent: 'KC', teamScore: 30, opponentScore: 21 }), 'W vs KC · 30–21');
  assert.equal(formatGame({ status: 'played', home: false, opponent: 'KC', teamScore: 14, opponentScore: 17 }), 'L @ KC · 14–17');
  assert.equal(formatGame({ status: 'played', home: false, opponent: 'KC', teamScore: 17, opponentScore: 17 }), 'T @ KC · 17–17');
  assert.equal(formatGame({ status: 'bye' }), 'Bye week');
  assert.equal(formatGame({ status: 'unavailable' }), 'No previous week');
});

test('escapes opponent in rendered result', () => {
  const markup = gameResult({ status: 'played', home: true, opponent: '<team>', teamScore: 7, opponentScore: 0 });
  assert.match(markup, /&lt;team&gt;/);
});

test('renders both weeks of the expandable schedule', () => {
  const games = {
    current: { status: 'played', home: true, opponent: '<KC>', teamScore: 30, opponentScore: 21 },
    previous: { status: 'bye' }
  };
  const summary = gameSummary(games, 12);
  assert.match(summary, /Week 12/);
  assert.match(summary, /W vs &lt;KC&gt; · 30–21/);
  assert.match(summary, /Week 11/);
  assert.match(summary, /Bye week/);
  assert.match(gameSummary({ ...games, previous: { status: 'unavailable' } }, 1), /Previous week.*No previous week/s);
});
