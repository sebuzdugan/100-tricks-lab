/** In-memory customer store (stand-in for the CRM). */
export const CUSTOMERS = {
  C1: { customerId: 'C1', name: 'Dana Ruiz', plan: 'pro', openTickets: 2 },
  C2: { customerId: 'C2', name: 'Sam Okafor', plan: 'free', openTickets: 0 },
};

/** Returns the customer with this id, or null. */
export function findCustomer(customerId) {
  return CUSTOMERS[customerId] ?? null;
}
