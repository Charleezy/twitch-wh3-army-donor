import test from 'node:test';
import assert from 'node:assert/strict';
import { parseConfig } from '../src/config.js';

test('parseConfig returns parsed JSON', () => {
  assert.deepEqual(parseConfig('{"a":1}'), { a: 1 });
});

test('parseConfig error never leaks file contents', () => {
  const bad = '{"socketToken": SECRETTOKENVALUE, "x": 1}';
  assert.throws(() => parseConfig(bad), (err) => {
    assert.ok(!err.message.includes('SECRET'));
    assert.match(err.message, /not valid JSON/);
    return true;
  });
});
