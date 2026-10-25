// Engine seam, desktop adapter: the same calls as engine/pyodide.js, answered by the native Python engine through the
// shell's bridge (src/t003gui/bridge.py, exposed by pywebview as window.pywebview.api).

export function createEngine() {
  const api = () => window.pywebview.api;
  const fromBase64 = (text) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
  return {
    async init() {
      if (!window.pywebview) await new Promise((resolve) => addEventListener("pywebviewready", resolve, { once: true }));
    },
    async options() {
      return JSON.parse(await api().options());
    },
    async preview(spec) {
      return fromBase64(await api().preview(JSON.stringify(spec)));
    },
  };
}
