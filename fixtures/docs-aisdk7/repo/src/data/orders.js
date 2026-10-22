/** In-memory order store (stand-in for the orders service). */
export const ORDERS = {
  A100: { orderId: 'A100', customerId: 'C1', status: 'shipped', eta: '2026-10-09' },
  A101: { orderId: 'A101', customerId: 'C1', status: 'processing', eta: '2026-10-14' },
  B200: { orderId: 'B200', customerId: 'C2', status: 'delivered', eta: '2026-10-02' },
  B201: { orderId: 'B201', customerId: 'C2', status: 'cancelled', eta: null },
};

/** Returns the order with this id, or null. */
export function findOrder(orderId) {
  return ORDERS[orderId] ?? null;
}
