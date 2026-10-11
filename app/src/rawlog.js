// Event types that flood the raw log (huge label totals, alert playback notices) and never carry donations.
const NOISY_EVENT_TYPES = new Set(['streamlabels', 'streamlabels.underlying', 'alertPlaying']);

export function shouldLogRawEvent(event) {
  return !(event && NOISY_EVENT_TYPES.has(event.type));
}
