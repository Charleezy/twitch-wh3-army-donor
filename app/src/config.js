import fs from 'node:fs';

export function loadConfig() {
  const url = new URL('../config.local.json', import.meta.url);
  if (!fs.existsSync(url)) {
    console.error('Missing app/config.local.json: copy config.example.json and fill it in.');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(url, 'utf8'));
}
