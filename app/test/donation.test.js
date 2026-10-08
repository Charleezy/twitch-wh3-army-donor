import test from 'node:test';
import assert from 'node:assert/strict';
import { parseDonations } from '../src/donation.js';

test('parses a Streamlabs donation event', () => {
  const event = {
    type: 'donation',
    event_id: 'evt_1',
    message: [{ id: 96164121, _id: 'abc123', name: 'Bob', amount: '13.37', currency: 'USD' }],
  };
  assert.deepEqual(parseDonations(event), [
    { id: 'abc123', donor: 'Bob', amount: 13.37, currency: 'USD', isTest: false },
  ]);
});

test('accepts for: streamlabs and flags test alerts', () => {
  const event = { type: 'donation', for: 'streamlabs', message: [{ id: 5, name: '', amount: 5, isTest: true }] };
  const [d] = parseDonations(event);
  assert.equal(d.id, '5');
  assert.equal(d.donor, 'Anonymous');
  assert.equal(d.currency, 'USD');
  assert.equal(d.isTest, true);
});

test('ignores non-donation events', () => {
  assert.deepEqual(parseDonations({ type: 'follow', message: [{}] }), []);
  assert.deepEqual(parseDonations({ type: 'bits', for: 'twitch_account', message: [{}] }), []);
  assert.deepEqual(parseDonations(null), []);
});

test('generates a unique id when the event carries none', () => {
  const event = { type: 'donation', message: [{ name: 'Bob', amount: 5 }, { name: 'Al', amount: 6 }] };
  const [a, b] = parseDonations(event);
  assert.match(a.id, /^gen-/);
  assert.notEqual(a.id, b.id);
});
