import test from 'node:test';
import assert from 'node:assert/strict';
import { setupPointTooltip } from '../dist/history-point-tooltip.js';

function events() {
  return {
    listeners: {},
    addEventListener(name, callback) { this.listeners[name] = callback; }
  };
}

test('point hover shows its team, week and rank and dismisses on exit', () => {
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  const previousElement = globalThis.Element;
  globalThis.Element = class {};
  const chart = events();
  const tooltip = { hidden: true, style: {}, offsetWidth: 140, offsetHeight: 30 };
  globalThis.window = { ...events(), innerWidth: 300, innerHeight: 200 };
  globalThis.document = events();
  try {
    const hide = setupPointTooltip(chart, tooltip);
    const move = (point, pointerType = 'mouse') => {
      const target = new Element();
      target.closest = () => point;
      chart.listeners.pointermove({ target, pointerType, clientX: 290, clientY: 190 });
    };
    const point = { dataset: { name: 'Buffalo Bills', week: '12', rank: '3' } };
    move(point);
    assert.equal(tooltip.textContent, 'Buffalo Bills · Week 12 · Rank 3');
    assert.equal(tooltip.hidden, false);
    assert.equal(tooltip.style.left, '152px');
    assert.equal(tooltip.style.top, '148px');
    move(null);
    assert.equal(tooltip.hidden, true);
    move(point);
    chart.listeners.pointerleave();
    assert.equal(tooltip.hidden, true);
    move(point);
    globalThis.document.listeners.keydown({ key: 'Escape' });
    assert.equal(tooltip.hidden, true);
    move(point, 'touch');
    assert.equal(tooltip.hidden, true);
    move(point);
    hide();
    assert.equal(tooltip.hidden, true);
  } finally {
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
    globalThis.Element = previousElement;
  }
});
