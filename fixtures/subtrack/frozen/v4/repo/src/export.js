import { nextCharge } from './cycles.js';
import { plainEuros } from './money.js';

const HEADER = ['name', 'price', 'cycle', 'monthly_cost', 'next_charge'];

// how many months one charge pays for
const MONTHS = { monthly: 1, yearly: 12 };

function cell(value) {
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * Subscriptions as CSV for a spreadsheet, one row per plan, with its monthly cost and next charge.
 * @param {Array<{ name: string, price: number, cycle: string, since: string }>} subs
 * @param {string} today 'YYYY-MM-DD'
 * @returns {string}
 */
export function toCsv(subs, today) {
  const lines = [HEADER.join(',')];
  for (const sub of subs) {
    const monthly = Math.floor(sub.price / MONTHS[sub.cycle]);
    lines.push([sub.name, plainEuros(sub.price), sub.cycle, plainEuros(monthly), nextCharge(sub, today)].map(cell).join(','));
  }
  return lines.join('\n') + '\n';
}
