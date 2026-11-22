import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parsePlayoffResponse, pollPlayoffPicture, waitForPlayoffRetry } from '../dist/playoff-poll.js';

test('distinguishes pending, valid pictures, and malformed responses', () => {
  const picture = { conferences: { AFC: [], NFC: [] } };
  const isPicture = value => Boolean(value?.conferences);
  assert.deepEqual(parsePlayoffResponse({ status: 'pending' }, isPicture), { pending: true, progress: null });
  assert.deepEqual(parsePlayoffResponse({ status: 'pending', progress: { completed: 25000, total: 100000 } }, isPicture),
    { pending: true, progress: { completed: 25000, total: 100000 } });
  assert.throws(() => parsePlayoffResponse({ status: 'pending', progress: { completed: 2, total: 1 } }, isPicture), /invalid simulation progress/);
  assert.deepEqual(parsePlayoffResponse(picture, isPicture), { pending: false, value: picture });
  for (const response of [null, {}, { status: 'failed' }]) {
    assert.throws(() => parsePlayoffResponse(response, isPicture), /invalid playoff response/);
  }
});

test('polls pending results and returns the completed picture', async () => {
  const controller = new AbortController();
  let calls = 0;
  let pending = 0;
  const picture = { season: 2025, week: 15 };
  const result = await pollPlayoffPicture(
    async () => ++calls < 3 ? { pending: true, progress: { completed: calls, total: 2 } } : { pending: false, value: picture },
    controller.signal, () => pending++, async () => {},
  );
  assert.equal(result, picture);
  assert.equal(calls, 3);
  assert.equal(pending, 2);
});

test('aborting stops polling and dismisses the retry timer', async () => {
  const controller = new AbortController();
  const pending = pollPlayoffPicture(
    async () => ({ pending: true, progress: null }), controller.signal, () => controller.abort(),
  );
  await assert.rejects(pending, { name: 'AbortError' });
  await assert.rejects(waitForPlayoffRetry(controller.signal), { name: 'AbortError' });
});

test('reports a calculation failure rather than retrying indefinitely', async () => {
  const controller = new AbortController();
  await assert.rejects(pollPlayoffPicture(
    async () => { throw new Error('Calculation failed'); },
    controller.signal, () => {},
  ), /Calculation failed/);
});
