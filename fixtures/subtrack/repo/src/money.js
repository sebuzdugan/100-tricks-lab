/**
 * Parse a euro amount typed by a person ("12", "12.5", "1,299.00") into whole cents.
 * Returns null when the text is not an amount.
 * @param {string} text
 * @returns {number | null}
 */
export function parseEuros(text) {
  const m = /^(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?$/.exec(String(text).trim());
  if (!m) return null;
  return Number(m[1].replace(/,/g, '')) * 100 + Number((m[2] ?? '').padEnd(2, '0'));
}

/**
 * Format whole cents as euros: 123456 -> "€1,234.56".
 * @param {number} cents
 * @returns {string}
 */
export function formatEuros(cents) {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  const euros = Math.floor(abs / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${sign}€${euros}.${String(abs % 100).padStart(2, '0')}`;
}

/**
 * Format whole cents as a plain decimal for files: 123456 -> "1234.56".
 * @param {number} cents
 * @returns {string}
 */
export function plainEuros(cents) {
  return (cents / 100).toFixed(2);
}
