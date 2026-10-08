// Queue file shared with the WH3 mod: one `id<TAB>donor<TAB>amount_usd` line per donation.
import fs from 'node:fs';

export function sanitizeDonor(name) {
  const clean = String(name ?? '').replace(/[\t\r\n]+/g, ' ').trim().slice(0, 40);
  return clean || 'Anonymous';
}

export function formatLine({ id, donor, amountUsd }) {
  return `${String(id).replace(/[\t\r\n]/g, '')}\t${sanitizeDonor(donor)}\t${amountUsd.toFixed(2)}\n`;
}

export function readIds(path) {
  if (!fs.existsSync(path)) return new Set();
  const lines = fs.readFileSync(path, 'utf8').split(/\r?\n/).filter(Boolean);
  return new Set(lines.map((line) => line.split('\t')[0]));
}

export function appendEntry(path, entry, seenIds) {
  if (seenIds.has(entry.id)) return false;
  fs.appendFileSync(path, formatLine(entry));
  seenIds.add(entry.id);
  return true;
}
