import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('rank header and column toggle are visible by default', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  assert.match(html, /<input\b[^>]*data-column-toggle="rank"[^>]*\bchecked\b/);
  const header = html.match(/<th\b[^>]*data-column="rank"[^>]*>/)?.[0];
  assert.ok(header);
  assert.doesNotMatch(header, /\bhidden\b/);
  assert.match(html, /data-sort="rank"/);
});

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
  const rankToggle = element({ columnToggle: 'rank' });
  rankToggle.checked = true;
  nodes['th[data-column="pointsFor"]'] = pointsHeader;
  nodes['th[data-column="rank"]'] = rankHeader;
  const document = {
    querySelector: key => nodes[key],
    querySelectorAll: key => ({
      '.filter': [],
      '.sort-button': [rankButton, pointsButton],
      '[data-column-toggle]': [rankToggle, pointsToggle],
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
  const ranks = () => [...nodes['#rankings-body'].innerHTML.matchAll(/<td class="rank-cell"(?: hidden)?><span>(\d+)<\/span><\/td>/g)].map(match => match[1]);
  try {
    await import('../dist/app.js');
    await flush();
    assert.deepEqual(order(), ['A', 'B']);
    assert.deepEqual(ranks(), ['01', '02']);
    assert.equal(rankHeader.attributes['aria-sort'], 'ascending');
    rankButton.dispatch('click');
    assert.deepEqual(order(), ['B', 'A']);
    assert.deepEqual(ranks(), ['02', '01']);
    assert.equal(rankHeader.attributes['aria-sort'], 'descending');

    nodes['#team-search'].value = 'Team A';
    nodes['#team-search'].dispatch('input');
    assert.deepEqual(order(), ['A']);
    assert.deepEqual(ranks(), ['01']);
    nodes['#team-search'].value = '';
    nodes['#team-search'].dispatch('input');
    pointsButton.dispatch('click');
    assert.equal(pointsHeader.attributes['aria-sort'], 'descending');
    nodes['#week-select'].value = '1';
    nodes['#week-select'].dispatch('change');
    assert.deepEqual(order(), ['B', 'A']);
    assert.deepEqual(ranks(), ['01', '02']);
    nodes['#team-search'].value = 'Team A';
    nodes['#team-search'].dispatch('input');
    assert.deepEqual(ranks(), ['02']);
    nodes['#team-search'].value = '';
    nodes['#team-search'].dispatch('input');
    assert.equal(pointsHeader.attributes['aria-sort'], 'descending');
    pointsButton.dispatch('click');
    assert.equal(pointsHeader.attributes['aria-sort'], 'ascending');
    assert.deepEqual(order(), ['A', 'B']);
    assert.deepEqual(ranks(), ['02', '01']);

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

    rankToggle.checked = false;
    rankToggle.dispatch('change');
    assert.equal(rankHeader.hidden, true);
    assert.match(nodes['#rankings-body'].innerHTML, /<td class="rank-cell" hidden>/);
    rankToggle.checked = true;
    rankToggle.dispatch('change');
    assert.equal(rankHeader.hidden, false);
    assert.match(nodes['#rankings-body'].innerHTML, /<td class="rank-cell"><span>01<\/span>/);
  } finally {
    Object.assign(globalThis, previous);
  }
});
