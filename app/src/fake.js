// Appends a fake donation to the queue: npm run fake -- <donor> <amountUsd>
import { loadConfig } from './config.js';
import { readIds, appendEntry } from './queue.js';

const [donor = 'Test Donor', amount = '5'] = process.argv.slice(2);
const config = loadConfig();
const id = `fake-${Date.now()}`;
appendEntry(config.queuePath, { id, donor, amountUsd: Number(amount) }, readIds(config.queuePath));
console.log(`Queued fake donation ${donor} $${Number(amount).toFixed(2)} (${id})`);
