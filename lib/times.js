// Pin times live in this browser, so no database change is needed.
const KEY = 'll_times_v1';
const read = () => { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch { return {}; } };
export const getTimes = () => (typeof localStorage === 'undefined' ? {} : read());
export function setTime(id, time) {
  try {
    const m = read();
    if (time) m[id] = time; else delete m[id];
    localStorage.setItem(KEY, JSON.stringify(m));
  } catch {}
}
