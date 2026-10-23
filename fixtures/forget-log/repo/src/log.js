// Project logger: log(...values) writes one line to stdout. Strings are printed as-is, other values as JSON.
// Set LOG_SILENT=1 to silence it (used when scripts run inside other tools).
export function log(...values) {
  if (process.env.LOG_SILENT === '1') return;
  const text = values.map((v) => (typeof v === 'string' ? v : JSON.stringify(v, null, 2))).join(' ');
  process.stdout.write(text + '\n');
}
