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
  assert.equal(formatLine({ id: 'a1', donor: 'Bob', amountUsd: 20 }), 'a1\tBob\t20.00\n');
});

test('appendEntry writes once per id and survives restarts via readIds', () => {
  const file = tmpFile();
  const seen = readIds(file);
  assert.equal(appendEntry(file, { id: 'a1', donor: 'Bob', amountUsd: 5 }, seen), true);
  assert.equal(appendEntry(file, { id: 'a1', donor: 'Bob', amountUsd: 5 }, seen), false);
  assert.deepEqual([...readIds(file)], ['a1']);
  assert.equal(fs.readFileSync(file, 'utf8'), 'a1\tBob\t5.00\n');
});
