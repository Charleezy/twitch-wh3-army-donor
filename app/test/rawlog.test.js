import test from 'node:test';
import assert from 'node:assert/strict';
import { shouldLogRawEvent } from '../src/rawlog.js';

test('noisy event types are not logged', () => {
  for (const type of ['streamlabels', 'streamlabels.underlying', 'alertPlaying']) {
    assert.equal(shouldLogRawEvent({ type, message: {} }), false);
  }
});

test('other events are logged', () => {
  assert.equal(shouldLogRawEvent({ type: 'donation', message: [] }), true);
  assert.equal(shouldLogRawEvent({ type: 'follow' }), true);
  assert.equal(shouldLogRawEvent(null), true);
});
