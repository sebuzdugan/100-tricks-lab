// The stored name of the new weekly cycle: whatever the run added to CYCLES next to monthly/yearly, else 'weekly'.
import * as cycles from '../src/cycles.js';
const extra = (cycles.CYCLES || []).filter((c) => c !== 'monthly' && c !== 'yearly');
export const WEEKLY = extra.find((c) => /week/i.test(c)) || extra[0] || 'weekly';
