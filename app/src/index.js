// Listens to Streamlabs donations and appends them to the WH3 mod's queue file.
import io from 'socket.io-client';
import { loadConfig } from './config.js';
import { toUsd } from './currency.js';
import { parseDonations } from './donation.js';
import fs from 'node:fs';
import path from 'node:path';
import { readIds, appendEntry, nowSeconds } from './queue.js';

function handle(config, seen, donation) {
  if (donation.isTest && !config.acceptTestAlerts) {
    console.log(`Skipped test alert from ${donation.donor}`);
    return;
  }
  // test alerts may reuse ids; give each its own so every click queues a spawn
  const id = donation.isTest ? `test-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` : donation.id;
  let usd = toUsd(donation.amount, donation.currency, config.currencyRates);
  if (usd === null) {
    console.warn(`Unknown currency ${donation.currency}; treating ${donation.amount} as USD`);
    usd = Number(donation.amount);
  }
  if (!Number.isFinite(usd)) {
    console.warn(`Ignored donation ${id}: amount ${donation.amount} is not a number`);
    return;
  }
  let added;
  try {
    added = appendEntry(config.queuePath, { id, donor: donation.donor, amountUsd: usd, time: nowSeconds() }, seen);
  } catch (err) {
    console.error(`Could not write donation ${id} (${donation.donor} $${usd.toFixed(2)}) to the queue: ${err.code || err.message}; re-add it with npm run fake -- "${donation.donor}" ${usd.toFixed(2)}`);
    return;
  }
  const via = donation.source === 'youtube_superchat' ? 'YouTube Super Chat' : 'Streamlabs';
  console.log(added ? `Queued ${donation.donor} $${usd.toFixed(2)} via ${via} (${id})` : `Duplicate ${id} ignored`);
}

const config = loadConfig();
if (!fs.existsSync(path.dirname(config.queuePath))) {
  console.error(`queuePath folder does not exist: ${path.dirname(config.queuePath)}. Fix queuePath in app/config.local.json.`);
  process.exit(1);
}
const seen = readIds(config.queuePath);
// token is in the URL: never log the URL
const socket = io(`https://sockets.streamlabs.com?token=${config.socketToken}`, { transports: ['websocket'] });
socket.on('connect', () => console.log('Connected to Streamlabs. Waiting for donations...'));
socket.on('connect_error', (err) => console.error(`Connection error: ${err.message}. Check socketToken in app/config.local.json.`));
socket.on('error', (err) => console.error(`Socket error: ${err && err.message ? err.message : err}`));
socket.on('disconnect', (reason) => console.warn(`Disconnected (${reason}). Donations sent while disconnected are lost.`));
socket.on('event', (event) => {
  if (config.logRawEvents) console.log(JSON.stringify(event));
  for (const donation of parseDonations(event)) handle(config, seen, donation);
});
