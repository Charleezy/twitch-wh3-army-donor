// Streamlabs Socket API: donations are { type: 'donation', for?: 'streamlabs', message: [...] }.
export function parseDonations(event) {
  if (!event || event.type !== 'donation' || !Array.isArray(event.message)) return [];
  if (event.for !== undefined && event.for !== 'streamlabs') return [];
  return event.message.map((m) => ({
    id: String(m._id ?? m.id ?? event.event_id ?? `gen-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`),
    donor: m.name || m.from || 'Anonymous',
    amount: Number(m.amount),
    currency: m.currency || 'USD',
    isTest: m.isTest === true,
  }));
}
