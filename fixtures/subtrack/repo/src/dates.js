// All dates are 'YYYY-MM-DD' strings and all maths is done in UTC, so the local time zone never matters.

const DAY_MS = 24 * 60 * 60 * 1000;
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function toUtc(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return Date.UTC(y, m - 1, d);
}

function fromUtc(ms) {
  return new Date(ms).toISOString().slice(0, 10);
}

/**
 * Check a date typed by a person. Returns the same 'YYYY-MM-DD' string, or null if it is not a real date.
 * @param {string} text
 * @returns {string | null}
 */
export function parseDate(text) {
  const s = String(text).trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  return fromUtc(toUtc(s)) === s ? s : null;
}

/**
 * Today's date in UTC.
 * @returns {string}
 */
export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Add whole days: addDays('2026-12-30', 3) -> '2027-01-02'.
 * @param {string} iso
 * @param {number} days
 * @returns {string}
 */
export function addDays(iso, days) {
  return fromUtc(toUtc(iso) + days * DAY_MS);
}

/**
 * Add whole months, keeping the day of the month or using the last day of a shorter month:
 * addMonths('2026-01-31', 1) -> '2026-02-28'.
 * @param {string} iso
 * @param {number} months
 * @returns {string}
 */
export function addMonths(iso, months) {
  const [y, m, d] = iso.split('-').map(Number);
  const first = new Date(Date.UTC(y, m - 1 + months, 1));
  const lastDay = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
  return fromUtc(Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), Math.min(d, lastDay)));
}

/**
 * Whole days from one date to another (negative if `to` is earlier).
 * @param {string} from
 * @param {string} to
 * @returns {number}
 */
export function daysBetween(from, to) {
  return Math.round((toUtc(to) - toUtc(from)) / DAY_MS);
}

/**
 * Short label for people: '2026-11-02' -> '2 Nov'.
 * @param {string} iso
 * @returns {string}
 */
export function shortLabel(iso) {
  const [, m, d] = iso.split('-').map(Number);
  return `${d} ${MONTH_NAMES[m - 1]}`;
}
