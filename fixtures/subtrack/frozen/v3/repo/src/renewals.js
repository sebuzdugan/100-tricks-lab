import { nextCharge } from './cycles.js';
import { daysBetween, shortLabel } from './dates.js';

/**
 * Charges coming up in the next `within` days (a charge today counts), soonest first.
 * @param {Array<{ name: string, price: number, cycle: string, since: string }>} subs
 * @param {string} today 'YYYY-MM-DD'
 * @param {number} [within=30]
 * @returns {Array<{ name: string, date: string, when: string, inDays: number, price: number, cycle: string }>}
 */
export function upcoming(subs, today, within = 30) {
  const rows = [];
  for (const sub of subs) {
    const date = nextCharge(sub, today);
    const inDays = daysBetween(today, date);
    if (inDays <= within) {
      rows.push({ name: sub.name, date, when: shortLabel(date), inDays, price: sub.price, cycle: sub.cycle });
    }
  }
  return rows.sort((a, b) => a.when.localeCompare(b.when) || a.name.localeCompare(b.name));
}
