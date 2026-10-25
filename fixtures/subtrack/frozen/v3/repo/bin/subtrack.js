#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { CYCLE, monthlyCents } from '../src/cycles.js';
import { parseDate, todayIso } from '../src/dates.js';
import { toCsv } from '../src/export.js';
import { formatEuros, parseEuros } from '../src/money.js';
import { upcoming } from '../src/renewals.js';
import { load, save, storePath, validate } from '../src/store.js';

const USAGE = `usage: subtrack <command> [options]

  add <name> <price> [--every month|year] [--since YYYY-MM-DD]
  list
  total
  renewals [--within <days>]
  export
  remove <name>

options for every command: --file <path>, --today YYYY-MM-DD`;

// how much of one charge falls in a month
const SHARE_PER_MONTH = { [CYCLE.MONTH]: 1, [CYCLE.YEAR]: 1 / 12 };

function die(message, code = 1) {
  process.stderr.write(`subtrack: ${message}\n`);
  process.exit(code);
}

// --every month|year (monthly/yearly work too)
const EVERY = { month: CYCLE.MONTH, monthly: CYCLE.MONTH, year: CYCLE.YEAR, yearly: CYCLE.YEAR };

function cycleFlag(value = 'month') {
  const cycle = EVERY[value.toLowerCase()];
  if (!cycle) die(`--every must be month or year, got "${value}"`, 2);
  return cycle;
}

let parsed;
try {
  parsed = parseArgs({
    args: process.argv.slice(2),
    allowPositionals: true,
    options: {
      every: { type: 'string' },
      since: { type: 'string' },
      within: { type: 'string' },
      today: { type: 'string' },
      file: { type: 'string' },
      help: { type: 'boolean', short: 'h' },
    },
  });
} catch (err) {
  die(`${err.message}\n\n${USAGE}`, 2);
}
const { values: opts, positionals } = parsed;
const [command, ...args] = positionals;
if (opts.help || !command) {
  console.log(USAGE);
  process.exit(command || opts.help ? 0 : 2);
}

const file = storePath(opts.file);
const today = opts.today === undefined ? todayIso() : parseDate(opts.today);
if (today === null) die(`--today must be a date (YYYY-MM-DD), got "${opts.today}"`, 2);

let subs;
try {
  subs = load(file);
} catch (err) {
  die(err.message);
}

switch (command) {
  case 'add': {
    const [name, priceText] = args;
    if (!name || priceText === undefined) die(`add needs a name and a price\n\n${USAGE}`, 2);
    const price = parseEuros(priceText);
    if (price === null) die(`"${priceText}" is not a price (try 12.99)`, 2);
    const since = opts.since === undefined ? today : parseDate(opts.since);
    if (since === null) die(`--since must be a date (YYYY-MM-DD), got "${opts.since}"`, 2);
    if (subs.some((s) => s.name.toLowerCase() === name.toLowerCase())) die(`${name} is already on the list`);
    const sub = { name, price, cycle: cycleFlag(opts.every), since };
    const problem = validate(sub);
    if (problem) die(problem, 2);
    subs.push(sub);
    save(file, subs);
    console.log(`Added ${name}: ${formatEuros(price)} ${sub.cycle}, ${formatEuros(monthlyCents(sub))} a month.`);
    break;
  }
  case 'list': {
    if (!subs.length) {
      console.log('No subscriptions yet. Add one with: subtrack add <name> <price>');
      break;
    }
    const width = Math.max(...subs.map((s) => s.name.length));
    for (const s of subs) {
      console.log(`${s.name.padEnd(width)}  ${formatEuros(s.price).padStart(10)} ${s.cycle.padEnd(8)} ${formatEuros(monthlyCents(s)).padStart(10)} a month`);
    }
    break;
  }
  case 'total': {
    // add up the exact amounts and cut to the cent once, so cut-off cents don't pile up across plans
    const total = Math.floor(subs.reduce((sum, s) => sum + s.price * (SHARE_PER_MONTH[s.cycle] ?? 0), 0) + 1e-9);
    console.log(`Monthly total: ${formatEuros(total)} (${subs.length} ${subs.length === 1 ? 'plan' : 'plans'})`);
    break;
  }
  case 'renewals': {
    const within = opts.within === undefined ? 30 : Number(opts.within);
    if (!Number.isInteger(within) || within < 0) die(`--within must be a whole number of days, got "${opts.within}"`, 2);
    const rows = upcoming(subs, today, within);
    if (!rows.length) {
      console.log(`Nothing renews in the next ${within} days.`);
      break;
    }
    const width = Math.max(...rows.map((r) => r.name.length));
    for (const r of rows) {
      console.log(`${r.when.padEnd(6)}  ${r.name.padEnd(width)}  ${formatEuros(r.price)}`);
    }
    break;
  }
  case 'export':
    process.stdout.write(toCsv(subs, today));
    break;
  case 'remove': {
    const [name] = args;
    const left = subs.filter((s) => s.name.toLowerCase() !== String(name).toLowerCase());
    if (left.length === subs.length) die(`${name} is not on the list`);
    save(file, left);
    console.log(`Removed ${name}.`);
    break;
  }
  default:
    die(`unknown command "${command}"\n\n${USAGE}`, 2);
}
