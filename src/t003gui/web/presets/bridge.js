// Presets seam, desktop adapter: the same presets.json the Qt app and `t003-print --preset` use, through the shell's
// bridge (src/t003gui/bridge.py). Same shape as presets/local.js.

export function createPresets() {
  const api = () => window.pywebview.api;
  const checked = (result) => {
    if (result.error) throw new Error(result.error);
    return result;
  };
  return {
    async list() {
      return (await api().presets_list()).names;
    },
    async get(name) {
      const result = await api().preset_get(name);
      return result.error ? null : JSON.parse(result.spec);
    },
    async save(name, label) {
      return checked(await api().preset_save(name, JSON.stringify(label))).saved;
    },
    async delete(name) {
      checked(await api().preset_delete(name));
    },
  };
}
