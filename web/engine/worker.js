// The Python engine in the browser: Pyodide in a worker, driving the same t003gui.api the desktop uses.
// Messages in: {id, method, args}; out: {id, result} or {id, error}; {progress} while loading.

let py = null;
let api = null;
let base = "";
const loadedFonts = new Set();

const progress = (text) => self.postMessage({ progress: text });

async function fetchBytes(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url}: ${response.status}`);
  return new Uint8Array(await response.arrayBuffer());
}

// The label's fonts are fetched the first time a label needs them (the whole set is 20 MB).
async function ensureFonts(specJson) {
  const needed = api.fonts_needed(specJson);
  const names = needed.toJs();
  needed.destroy();
  for (const name of names) {
    if (loadedFonts.has(name)) continue;
    py.FS.writeFile(`/pkg/t003gui/fonts/${name}`, await fetchBytes(`${base}fonts/${encodeURIComponent(name)}`));
    loadedFonts.add(name);
  }
}

// A Python `bytes` result as a Uint8Array we own.
function takeBytes(proxy) {
  const bytes = proxy.toJs();
  proxy.destroy();
  return bytes;
}

const handlers = {
  async init({ baseUrl }) {
    base = baseUrl;
    const manifest = await (await fetch(`${base}engine/manifest.json`)).json();
    progress("Loading Python…");
    const { loadPyodide } = await import(`https://cdn.jsdelivr.net/pyodide/v${manifest.pyodide}/full/pyodide.mjs`);
    py = await loadPyodide();
    progress("Loading Pillow…");
    await py.loadPackage(manifest.packages);
    await py.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(manifest.pypi)})`);
    progress("Loading the label engine…");
    py.FS.mkdirTree("/pkg/t003gui/fonts");
    for (const name of manifest.python) {
      py.FS.writeFile(`/pkg/t003gui/${name}`, await fetchBytes(`${base}engine/${name}`));
    }
    py.runPython("import sys; sys.path.insert(0, '/pkg')");
    api = py.pyimport("t003gui.api");
    return null;
  },
  async options() {
    return api.options();
  },
  async preview({ spec }) {
    await ensureFonts(spec);
    const pixels = takeBytes(api.preview_pixels(spec));
    const hints = api.hints(spec);
    const list = hints.toJs();
    hints.destroy();
    return { pixels, hints: list };
  },
  async tspl({ spec }) {
    await ensureFonts(spec);
    return takeBytes(api.tspl_bytes(spec));
  },
  async statusProblems({ status }) {
    const problems = api.status_problems(status);
    const list = problems.toJs();
    problems.destroy();
    return list;
  },
};

self.onmessage = async ({ data: { id, method, args } }) => {
  try {
    const result = await handlers[method](args || {});
    const buffers = result instanceof Uint8Array ? [result.buffer] : result && result.pixels instanceof Uint8Array ? [result.pixels.buffer] : [];
    self.postMessage({ id, result }, buffers);
  } catch (e) {
    self.postMessage({ id, error: String((e && e.message) || e) });
  }
};
