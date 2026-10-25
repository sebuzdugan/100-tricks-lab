import { addMonths } from './dates.js';

/** Billing cycles a plan can have. */
export const CYCLE = Object.freeze({ MONTH: 'monthly', YEAR: 'yearly' });

/** Every supported cycle, as stored in the subscriptions file. */
export const CYCLES = Object.freeze(Object.values(CYCLE));

const MONTHS_PER_CHARGE = { [CYCLE.MONTH]: 1, [CYCLE.YEAR]: 12 };

/**
 * What a plan costs per month, in whole cents (cut to the cent).
 * @param {{ price: number, cycle: string }} sub
 * @returns {number}
 */
export function monthlyCents(sub) {
  return Math.floor(sub.price / MONTHS_PER_CHARGE[sub.cycle]);
}

/**
 * The date of a plan's next charge on or after `today` ('YYYY-MM-DD').
 * Charges fall on the day of the month of the first charge (`since`), or the last day of a shorter month.
 * @param {{ cycle: string, since: string }} sub
 * @param {string} today
 * @returns {string}
 */
export function nextCharge(sub, today) {
  const step = MONTHS_PER_CHARGE[sub.cycle];
  let n = 0;
  let date = sub.since;
  while (date < today) {
    n += 1;
    date = addMonths(sub.since, n * step);
  }
  return date;
}
