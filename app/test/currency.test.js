import test from 'node:test';
import assert from 'node:assert/strict';
import { toUsd } from '../src/currency.js';

const rates = { USD: 1, EUR: 1.1 };

test('converts known currencies and rounds to cents', () => {
  assert.equal(toUsd('10', 'EUR', rates), 11);
  assert.equal(toUsd(13.371, 'usd', rates), 13.37);
});

test('unknown currency or bad amount gives null', () => {
  assert.equal(toUsd(5, 'JPY', rates), null);
  assert.equal(toUsd('abc', 'USD', rates), null);
});

test('missing currency means USD', () => {
  assert.equal(toUsd(5, undefined, rates), 5);
});
