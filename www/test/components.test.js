import test from 'node:test';
import assert from 'node:assert/strict';

test('team badges use a white logo background and restore the colored fallback on error', async () => {
  const previousDocument = globalThis.document;
  const previousImage = globalThis.HTMLImageElement;
  let onError;
  globalThis.document = { addEventListener(type, handler) { if (type === 'error') onError = handler; } };
  globalThis.HTMLImageElement = class {};
  try {
    const { badge } = await import('../dist/components.js');
    const team = { id: 'KC', color: '#e31837', logo: 'https://example.com/kc.png' };
    assert.match(badge(team), /class="team-badge team-badge-with-logo"/);
    assert.match(badge(team, true), /class="team-badge team-badge-large team-badge-with-logo"/);
    assert.doesNotMatch(badge({ ...team, logo: '' }), /team-badge-with-logo/);
    assert.doesNotMatch(badge({ ...team, logo: 'http://example.com/kc.png' }), /team-badge-with-logo/);

    const image = new HTMLImageElement();
    const removed = [];
    image.matches = selector => selector === '.team-badge img';
    image.parentElement = { classList: { remove: name => removed.push(name) } };
    onError({ target: image });
    assert.equal(image.hidden, true);
    assert.deepEqual(removed, ['team-badge-with-logo']);
  } finally {
    globalThis.document = previousDocument;
    globalThis.HTMLImageElement = previousImage;
  }
});
