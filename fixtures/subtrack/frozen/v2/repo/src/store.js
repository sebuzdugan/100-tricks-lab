import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { CYCLE, CYCLES } from './cycles.js';
import { parseDate } from './dates.js';

/**
 * Where the subscriptions are kept: `--file`, else $SUBTRACK_FILE, else ./subscriptions.json.
 * @param {string | undefined} file
 * @param {Record<string, string | undefined>} [env=process.env]
 * @returns {string}
 */
export function storePath(file, env = process.env) {
  return file || env.SUBTRACK_FILE || 'subscriptions.json';
}

/**
 * Why a subscription is not valid, or null if it is.
 * @param {{ name: string, price: number, cycle: string, since: string }} sub
 * @returns {string | null}
 */
export function validate(sub) {
  if (!sub || typeof sub.name !== 'string' || !sub.name.trim()) return 'a subscription needs a name';
  if (!Number.isInteger(sub.price) || sub.price < 0) return `${sub.name}: price must be whole cents, zero or more`;
  if (!CYCLES.includes(sub.cycle)) return `${sub.name}: unknown billing cycle "${sub.cycle}"`;
  if (parseDate(sub.since) === null) return `${sub.name}: "since" must be a date (YYYY-MM-DD)`;
  return null;
}

// Files written by subtrack 0.1 stored "month" and "year"; read them with today's cycle names.
function upgrade(sub) {
  return { ...sub, cycle: sub.cycle === 'yearly' || sub.cycle === 'year' ? CYCLE.YEAR : CYCLE.MONTH };
}

/**
 * Read every subscription from the file (none if it does not exist yet). Throws on an invalid entry.
 * @param {string} path
 * @returns {Array<{ name: string, price: number, cycle: string, since: string }>}
 */
export function load(path) {
  if (!existsSync(path)) return [];
  const subs = (JSON.parse(readFileSync(path, 'utf8')).subscriptions ?? []).map(upgrade);
  for (const sub of subs) {
    const problem = validate(sub);
    if (problem) throw new Error(`${path}: ${problem}`);
  }
  return subs;
}

/**
 * Write every subscription to the file.
 * @param {string} path
 * @param {Array<{ name: string, price: number, cycle: string, since: string }>} subs
 */
export function save(path, subs) {
  writeFileSync(path, JSON.stringify({ subscriptions: subs }, null, 2) + '\n');
}
