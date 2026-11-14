import test from 'node:test';
import assert from 'node:assert/strict';
import { setupRankingsExpansion } from '../dist/rankings-expansion.js';

function row(id) {
  const attributes = { 'aria-expanded': 'false' };
  const button = {
    getAttribute: name => attributes[name],
    setAttribute: (name, value) => { attributes[name] = value; }
  };
  const details = { hidden: true };
  return {
    dataset: { team: id }, button, details,
    querySelector: selector => selector === '.rankings-team-button' ? button : details
  };
}

test('individual rows toggle, preserve independent state, and reset', () => {
  const previousElement = globalThis.Element;
  globalThis.Element = class {};
  try {
  let click;
  const first = row('A');
  const second = row('B');
  const body = {
    addEventListener: (type, handler) => { if (type === 'click') click = handler; },
    contains: target => target === first || target === second
  };
  const expansion = setupRankingsExpansion(body);
  const select = row => {
    const target = new Element();
    target.closest = () => row;
    click({ target });
  };
  select(first);
  assert.equal(first.button.getAttribute('aria-expanded'), 'true');
  assert.equal(first.details.hidden, false);
  assert.equal(expansion.isExpanded('A'), true);
  select(second);
  select(first);
  assert.equal(first.details.hidden, true);
  assert.equal(expansion.isExpanded('A'), false);
  assert.equal(expansion.isExpanded('B'), true);
  select(null);
  select(row('C'));
  assert.equal(expansion.isExpanded('C'), false);
  expansion.reset();
  assert.equal(expansion.isExpanded('B'), false);
  } finally {
    globalThis.Element = previousElement;
  }
});
