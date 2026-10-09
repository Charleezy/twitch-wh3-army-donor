// Queue file shared with the WH3 mod: one `id<TAB>donor<TAB>amount_usd<TAB>epoch_seconds` line per donation.
import fs from 'node:fs';

export function sanitizeDonor(name) {
  const clean = String(name ?? '').replace(/[\t\r\n]+/g, ' ').trim().slice(0, 40);
  return clean || 'Anonymous';
}

export const nowSeconds = () => Math.floor(Date.now() / 1000);

// `time` is unix epoch seconds; the mod uses it to skip donations queued long before a save was loaded
export function formatLine({ id, donor, amountUsd, time = nowSeconds() }) {
  return `${String(id).replace(/[\t\r\n]/g, '')}\t${sanitizeDonor(donor)}\t${amountUsd.toFixed(2)}\t${Math.floor(time)}\n`;
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
