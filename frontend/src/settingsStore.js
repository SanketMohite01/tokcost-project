const KEY = "tokcost_settings";

const DEFAULTS = {
  contextEnabled: true,
  maxContextMessages: 8,
  contextCharBudget: 4000,
  sidebarHidden: false,
};

export function loadSettings() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULTS };
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch (e) {
    return { ...DEFAULTS };
  }
}

export function saveSettings(partial) {
  const next = { ...loadSettings(), ...partial };
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}

export { DEFAULTS };
