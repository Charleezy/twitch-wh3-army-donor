// Streamlabs Socket API events we turn into spawns:
//  - tips:        { type: 'donation', for?: 'streamlabs', message: [{ amount: '13.37', ... }] }
//  - Super Chats: { type: 'superchat', for: 'youtube_account', message: [{ amount: '2000000', ... }] }
//    (amount is in millionths of the currency unit, per Streamlabs' documented example:
//    "2000000" with displayString "$2.00"; confirm with a real/test Super Chat via logRawEvents).
// Everything else (bits, subscriptions, follows...) is ignored.
export function parseDonations(event) {
  if (!event || !Array.isArray(event.message)) return [];
  let source;
  if (event.type === 'donation' && (event.for === undefined || event.for === 'streamlabs')) source = 'streamlabs';
  else if (event.type === 'superchat' && event.for === 'youtube_account') source = 'youtube_superchat';
  else return [];
  return event.message.map((m) => ({
    id: String(m._id ?? m.id ?? event.event_id ?? `gen-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`),
    donor: m.name || m.from || 'Anonymous',
    amount: source === 'youtube_superchat' ? Number(m.amount) / 1_000_000 : Number(m.amount),
    currency: m.currency || 'USD',
    isTest: m.isTest === true,
    source,
  }));
}
