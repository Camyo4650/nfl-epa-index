import test from 'node:test';
import assert from 'node:assert/strict';

function element(dataset = {}) {
  return {
    dataset, listeners: {}, attributes: {}, value: '', hidden: false, checked: false,
    addEventListener(type, listener) { this.listeners[type] = listener; },
    dispatch(type) { this.listeners[type](); },
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; },
    querySelector() { return this.arrow; },
    classList: { toggle() {} }
  };
}

function select() {
  const node = element();
  Object.defineProperty(node, 'innerHTML', {
    set(html) {
      this.value = /<option value="([^"]+)"/.exec(html)?.[1] ?? '';
    }
  });
  return node;
}

function team(id, rank, points) {
  return {
    id, name: `Team ${id}`, rank, conference: 'AFC', division: 'East',
    color: '#111111', logo: '', epa: 0.1, strengthOfScheduleRank: 1,
    record: { wins: 1, losses: 0, ties: 0 }, previousRank: null, change: null,
    points: { for: points, allowed: 0, net: points },
    games: { current: { status: 'bye' }, previous: { status: 'unavailable' } }
  };
}

test('sort column and direction survive week, metric and season changes', async () => {
  const nodes = Object.fromEntries([
    '#team-search', '#leaders', '#rankings-body', '#empty-state', '#result-count',
    '#comparison-label', '#metric-label', '#data-status', '#refresh-status',
    '[data-game-week="current"]', '[data-game-week="previous"]'
  ].map(key => [key, element()]));
  nodes['#season-select'] = select();
  nodes['#week-select'] = select();
  nodes['#metric-select'] = select();
  nodes['#metric-select'].value = 'combined';
  const pointsHeader = element();
  const rankHeader = element();
  const pointsButton = element({ sort: 'pointsFor' });
  pointsButton.parentElement = pointsHeader;
  pointsButton.arrow = element();
  const rankButton = element({ sort: 'rank' });
  rankButton.parentElement = rankHeader;
  rankButton.arrow = element();
  const pointsToggle = element({ columnToggle: 'pointsFor' });
  pointsToggle.checked = true;
  nodes['th[data-column="pointsFor"]'] = pointsHeader;
  const document = {
    querySelector: key => nodes[key],
    querySelectorAll: key => ({
      '.filter': [],
      '.sort-button': [rankButton, pointsButton],
      '[data-column-toggle]': [pointsToggle],
      '.site-nav a:not([aria-current="page"])': []
    })[key],
    addEventListener() {}
  };
  const week = (a, b) => [team('A', 1, a), team('B', 2, b)];
  const seasons = {
    2024: { weeks: {
      1: { combined: week(1, 5), offense: week(6, 2) },
      2: { combined: week(7, 3), offense: week(1, 9) }
    } },
    2023: { weeks: { 1: { combined: week(4, 8), offense: week(8, 4) } } }
  };
  let releaseSeason;
  const seasonPending = new Promise(resolve => { releaseSeason = resolve; });
  const previous = {
    document: globalThis.document, location: globalThis.location,
    fetch: globalThis.fetch, setInterval: globalThis.setInterval
  };
  globalThis.document = document;
  globalThis.location = { search: '' };
  globalThis.setInterval = () => 0;
  globalThis.fetch = async url => {
    let data;
    if (url === '/api/status') data = { lastSuccessfulRefresh: '2024-01-01', latestSeason: 2024 };
    else if (url === '/api/seasons') data = { seasons: [2024, 2023] };
    else {
      const season = new URL(url, 'http://localhost').searchParams.get('season');
      if (season === '2023') await seasonPending;
      data = seasons[season];
    }
    return { ok: true, json: async () => data };
  };
  const flush = () => new Promise(resolve => setImmediate(resolve));
  const order = () => [...nodes['#rankings-body'].innerHTML.matchAll(/<strong>Team ([AB])<\/strong>/g)].map(match => match[1]);
  try {
    await import('../dist/app.js');
    await flush();
    assert.deepEqual(order(), ['A', 'B']);
    pointsButton.dispatch('click');
    assert.equal(pointsHeader.attributes['aria-sort'], 'descending');
    nodes['#week-select'].value = '1';
    nodes['#week-select'].dispatch('change');
    assert.deepEqual(order(), ['B', 'A']);
    assert.equal(pointsHeader.attributes['aria-sort'], 'descending');
    pointsButton.dispatch('click');
    assert.equal(pointsHeader.attributes['aria-sort'], 'ascending');
    assert.deepEqual(order(), ['A', 'B']);

    nodes['#week-select'].value = '2';
    nodes['#week-select'].dispatch('change');
    assert.deepEqual(order(), ['B', 'A']);
    assert.equal(pointsHeader.attributes['aria-sort'], 'ascending');
    nodes['#metric-select'].value = 'offense';
    nodes['#metric-select'].dispatch('change');
    assert.deepEqual(order(), ['A', 'B']);
    assert.equal(pointsHeader.attributes['aria-sort'], 'ascending');

    nodes['#season-select'].value = '2023';
    nodes['#season-select'].dispatch('change');
    assert.equal(nodes['#rankings-body'].innerHTML, '');
    releaseSeason();
    await flush();
    assert.deepEqual(order(), ['B', 'A']);
    assert.equal(pointsHeader.attributes['aria-sort'], 'ascending');

    pointsToggle.checked = false;
    pointsToggle.dispatch('change');
    assert.deepEqual(order(), ['A', 'B']);
    assert.equal(rankHeader.attributes['aria-sort'], 'ascending');
    assert.equal(pointsHeader.hidden, true);
  } finally {
    Object.assign(globalThis, previous);
  }
});
