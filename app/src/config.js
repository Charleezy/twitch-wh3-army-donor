import fs from 'node:fs';

// Never include JSON.parse's raw message: Node embeds a snippet of the file (which holds the token).
export function parseConfig(text) {
  try {
    return JSON.parse(text);
  } catch (err) {
    const where = /position \d+|line \d+ column \d+/.exec(String(err.message));
    throw new Error('app/config.local.json is not valid JSON (use \\ or / in Windows paths)' + (where ? ` at ${where[0]}` : ''));
  }
}

export function loadConfig() {
  const url = new URL('../config.local.json', import.meta.url);
  if (!fs.existsSync(url)) {
    console.error('Missing app/config.local.json: copy config.example.json and fill it in.');
    process.exit(1);
  }
  try {
    return parseConfig(fs.readFileSync(url, 'utf8'));
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
}
