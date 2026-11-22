import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('playoff cards show relevant labels without an outside-top-seven label', async () => {
  const previousDocument = globalThis.document;
  globalThis.document = { addEventListener() {} };
  try {
    const { renderPlayoffTeams } = await import('../dist/playoff-cards.js');
    const team = {
      id: 'KC', name: 'Kansas City', conference: 'AFC', division: 'West',
      color: '#123456', record: { wins: 3, losses: 10, ties: 0 },
      rank: 10, divisionLeader: false, probability: 0.125, status: 'undetermined'
    };
    const outside = renderPlayoffTeams([team]);
    assert.doesNotMatch(outside, /OUTSIDE TOP SEVEN|<small>/);
    assert.doesNotMatch(outside, /playoff-card-eliminated/);
    assert.match(outside, /12\.5%/);
    const eliminated = renderPlayoffTeams([{ ...team, status: 'eliminated' }]);
    assert.match(eliminated, /<small>ELIMINATED<\/small>/);
    assert.match(eliminated, /class="playoff-card playoff-card-eliminated"/);
    assert.match(renderPlayoffTeams([{ ...team, rank: 7, status: 'eliminated' }]),
      /class="playoff-card playoff-card-in playoff-card-eliminated"/);
    assert.doesNotMatch(eliminated, / · ELIMINATED|Eliminated by record/);
    assert.match(renderPlayoffTeams([{ ...team, rank: 7 }]), /<small>WILD CARD<\/small>/);
    assert.match(renderPlayoffTeams([{ ...team, rank: 1, divisionLeader: true, status: 'locked_in' }], true),
      /<small>DIVISION LEADER · CLINCHED<\/small>/);
    assert.match(renderPlayoffTeams([{ ...team, status: 'eliminated' }], true), /FINAL RESULT/);
    const html = await readFile(new URL('../playoffs.html', import.meta.url), 'utf8');
    assert.match(html, /id="playoff-source"/);
  } finally {
    globalThis.document = previousDocument;
  }
});
