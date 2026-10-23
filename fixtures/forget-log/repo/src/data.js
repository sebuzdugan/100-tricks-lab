import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const DEFAULT_PATH = fileURLToPath(new URL('../data/orders.json', import.meta.url));

/** Reads the orders file (default: data/orders.json) and returns the array of orders. */
export function loadOrders(path = DEFAULT_PATH) {
  return JSON.parse(readFileSync(path, 'utf8'));
}
