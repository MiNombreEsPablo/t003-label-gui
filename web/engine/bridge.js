// Engine seam, desktop adapter: the same calls as engine/pyodide.js, answered by the native Python engine through the
// shell's bridge (src/t003gui/bridge.py, exposed by pywebview as window.pywebview.api).

export function createEngine() {
  const api = () => window.pywebview.api;
  const fromBase64 = (text) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
  return {
    // `window.pywebview` exists before its methods do, so wait for the methods themselves, not just the object.
    async init() {
      const ready = () => window.pywebview && window.pywebview.api && typeof window.pywebview.api.options === "function";
      for (let waited = 0; !ready(); waited += 50) {
        if (waited >= 15000) throw new Error("The desktop bridge didn't start. Close the window and open it again.");
        await new Promise((resolve) => setTimeout(resolve, 50));
      }
    },
    async options() {
      return JSON.parse(await api().options());
    },
    async preview(spec) {
      const result = await api().preview(JSON.stringify(spec));
      return { pixels: fromBase64(result.pixels), hints: result.hints };
    },
  };
}
