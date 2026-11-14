import test from 'node:test';
import assert from 'node:assert/strict';
import { setupMovementExpansion } from '../dist/movement-expansion.js';

function target() {
  return {
    listeners: {},
    addEventListener(event, listener) { this.listeners[event] = listener; },
    click(event = {}) { this.listeners.click(event); }
  };
}

function makeRow() {
  let state = 'false';
  const button = {
    getAttribute: () => state,
    setAttribute: (_, value) => { state = value; }
  };
  const details = { hidden: true };
  return {
    button, details,
    querySelector(selector) { return selector === '.chart-team-button' ? button : details; }
  };
}

test('bulk and individual controls stay synchronized as rows change', () => {
  const previousElement = globalThis.Element;
  globalThis.Element = class {};
  try {
  let rows = [makeRow(), makeRow()];
  const container = {
    ...target(),
    contains: row => rows.includes(row),
    querySelectorAll(selector) {
      return selector === '.chart-row' ? rows : rows.map(row => row.button);
    }
  };
  const expand = target();
  const collapse = target();
  const update = setupMovementExpansion(container, expand, collapse);
  update();
  assert.equal(expand.disabled, false);
  assert.equal(collapse.disabled, true);

  expand.click();
  assert.ok(rows.every(row => !row.details.hidden && row.button.getAttribute('aria-expanded') === 'true'));
  assert.equal(expand.disabled, true);
  assert.equal(collapse.disabled, false);

  const clicked = new Element();
  clicked.closest = () => rows[0];
  container.click({ target: clicked });
  assert.equal(rows[0].details.hidden, true);
  assert.equal(rows[0].button.getAttribute('aria-expanded'), 'false');
  assert.equal(expand.disabled, false);
  assert.equal(collapse.disabled, false);

  collapse.click();
  assert.ok(rows.every(row => row.details.hidden && row.button.getAttribute('aria-expanded') === 'false'));
  assert.equal(collapse.disabled, true);
  rows = [];
  update();
  assert.equal(expand.disabled, true);
  assert.equal(collapse.disabled, true);
  rows = [makeRow()];
  update();
  assert.equal(expand.disabled, false);
  assert.equal(collapse.disabled, true);
  } finally {
    globalThis.Element = previousElement;
  }
});
