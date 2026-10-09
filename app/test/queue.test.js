import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { sanitizeDonor, formatLine, readIds, appendEntry } from '../src/queue.js';

const tmpFile = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'dsa-')), 'queue.txt');

test('sanitizeDonor strips separators, trims, caps length, defaults', () => {
  assert.equal(sanitizeDonor(' Bob\tthe\nGreat '), 'Bob the Great');
  assert.equal(sanitizeDonor('x'.repeat(60)).length, 40);
  assert.equal(sanitizeDonor(''), 'Anonymous');
  assert.equal(sanitizeDonor(undefined), 'Anonymous');
});

test('formatLine matches the mod format', () => {
  assert.equal(formatLine({ id: 'a1', donor: 'Bob', amountUsd: 20, time: 1760000000 }), 'a1\tBob\t20.00\t1760000000\n');
});

test('formatLine defaults the time to now, in epoch seconds', () => {
  const before = Math.floor(Date.now() / 1000);
  const time = Number(formatLine({ id: 'a1', donor: 'Bob', amountUsd: 20 }).trim().split('\t')[3]);
  assert.ok(Number.isInteger(time) && time >= before && time <= before + 5);
});

test('readIds reads both 3-field legacy lines and 4-field lines', () => {
  const file = tmpFile();
  fs.writeFileSync(file, 'old1\tBob\t5.00\nnew1\tAmy\t7.00\t1760000000\n');
  assert.deepEqual([...readIds(file)], ['old1', 'new1']);
});

test('appendEntry writes once per id and survives restarts via readIds', () => {
  const file = tmpFile();
  const seen = readIds(file);
  assert.equal(appendEntry(file, { id: 'a1', donor: 'Bob', amountUsd: 5, time: 100 }, seen), true);
  assert.equal(appendEntry(file, { id: 'a1', donor: 'Bob', amountUsd: 5 }, seen), false);
  assert.deepEqual([...readIds(file)], ['a1']);
  assert.equal(fs.readFileSync(file, 'utf8'), 'a1\tBob\t5.00\t100\n');
});
