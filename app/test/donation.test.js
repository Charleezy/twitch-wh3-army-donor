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
    { id: 'abc123', donor: 'Bob', amount: 13.37, currency: 'USD', isTest: false, source: 'streamlabs' },
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

const superchat = (over = {}, msg = {}) => ({
  type: 'superchat',
  for: 'youtube_account',
  message: [{
    id: 'UgzX', channelId: 'UC1', channelUrl: 'https://youtube.com/channel/UC1', name: 'Kappa Lord',
    comment: 'hi', amount: '2000000', currency: 'USD', displayString: '$2.00', messageType: 2,
    createdAt: '1', _id: 'sc_1', ...msg,
  }],
  ...over,
});

test('parses the documented YouTube Super Chat example', () => {
  assert.deepEqual(parseDonations(superchat()), [
    { id: 'sc_1', donor: 'Kappa Lord', amount: 2, currency: 'USD', isTest: false, source: 'youtube_superchat' },
  ]);
});

test('Super Chat falls back to id, Anonymous and USD', () => {
  const [d] = parseDonations(superchat({}, { _id: undefined, name: '', currency: undefined, amount: '50000000' }));
  assert.equal(d.id, 'UgzX');
  assert.equal(d.donor, 'Anonymous');
  assert.equal(d.currency, 'USD');
  assert.equal(d.amount, 50);
});

test('Super Chat passes non-USD currency through for index.js to convert', () => {
  const [d] = parseDonations(superchat({}, { amount: '5500000', currency: 'EUR' }));
  assert.equal(d.amount, 5.5);
  assert.equal(d.currency, 'EUR');
});

test('Super Chat with a non-numeric amount yields NaN so index.js skips it', () => {
  const [d] = parseDonations(superchat({}, { amount: 'abc' }));
  assert.ok(Number.isNaN(d.amount));
});

test('ignores superchat events for other accounts', () => {
  assert.deepEqual(parseDonations(superchat({ for: 'twitch_account' })), []);
  assert.deepEqual(parseDonations(superchat({ for: undefined })), []);
});

test('still ignores bits and subscriptions', () => {
  assert.deepEqual(parseDonations({ type: 'bits', for: 'twitch_account', message: [{ amount: 100 }] }), []);
  assert.deepEqual(parseDonations({ type: 'subscription', for: 'twitch_account', message: [{ name: 'x' }] }), []);
  assert.deepEqual(parseDonations({ type: 'subscription', for: 'youtube_account', message: [{ name: 'x' }] }), []);
});
