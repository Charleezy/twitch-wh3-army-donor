// Streamlabs sends the donor's currency and no USD figure; rates come from config.
export function toUsd(amount, currency, rates) {
  const value = Number(amount);
  if (!Number.isFinite(value)) return null;
  const rate = rates[(currency || 'USD').toUpperCase()];
  if (rate === undefined) return null;
  return Math.round(value * rate * 100) / 100;
}
