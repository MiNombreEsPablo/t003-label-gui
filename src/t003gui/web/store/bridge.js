// Store seam, desktop adapter: the same calls, kept by the shell in the config folder (src/t003gui/settings.py).

export function createStore() {
  const api = () => window.pywebview.api;
  return {
    async get(key, fallback) {
      const value = await api().get_setting(key, null);
      return value === null || value === undefined ? fallback : value;
    },
    async set(key, value) {
      await api().set_setting(key, value);
    },
  };
}
