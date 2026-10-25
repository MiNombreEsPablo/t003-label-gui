// The UI, written once. It only ever talks to three seams, whichever client it runs in:
//   engine:  options(), preview(spec) -> {pixels, hints}                 (engine/pyodide.js or engine/bridge.js)
//   printer: modes, print(spec, {mode, address}) -> {problems, error}    (printer/ble.js or printer/bridge.js)
//   store:   get(key, fallback), set(key, value)                         (store/local.js or store/bridge.js)
// The desktop shell opens this page with ?client=desktop; anywhere else it is the browser build.
// The label's simple controls are built from the description the engine provides (form.js).

import { buildForm } from "./form.js";

const desktop = new URLSearchParams(location.search).get("client") === "desktop";
const $ = (id) => document.getElementById(id);
const status = (text, isError = false) => {
  $("status").textContent = text;
  $("status").classList.toggle("error", isError);
};

async function connectSeams() {
  if (desktop) {
    const [engineModule, printerModule, storeModule] = await Promise.all([
      import("./engine/bridge.js"), import("./printer/bridge.js"), import("./store/bridge.js"),
    ]);
    const engine = engineModule.createEngine();
    await engine.init();
    return { engine, store: storeModule.createStore(), makePrinter: () => printerModule.createPrinter() };
  }
  const [engineModule, printerModule, storeModule] = await Promise.all([
    import("./engine/pyodide.js"), import("./printer/ble.js"), import("./store/local.js"),
  ]);
  const engine = engineModule.createEngine(new URL("./", location.href).href);
  await engine.init(status);
  return { engine, store: storeModule.createStore(), makePrinter: (options) => printerModule.createPrinter(engine, options) };
}

async function main() {
  status("Starting…");
  const { engine, store, makePrinter } = await connectSeams();
  const options = await engine.options();
  const printer = makePrinter(options);
  const { width, sticker_height: stickerHeight } = options.geometry;

  const canvas = $("preview");
  canvas.width = width;
  canvas.height = stickerHeight; // the gap between stickers is never printed: the page captions it under the canvas
  const context = canvas.getContext("2d");

  // Render the newest request only: while one is running, later keystrokes just replace the waiting one.
  let rendering = false;
  let again = false;
  let last = null;
  async function refresh() {
    if (rendering) {
      again = true;
      return;
    }
    rendering = true;
    try {
      do {
        again = false;
        const { pixels, hints } = await engine.preview(spec());
        draw(pixels);
        $("hint").textContent = hints.join(" ");
        $("hint").hidden = hints.length === 0;
      } while (again);
      if ($("status").classList.contains("error")) status("");
    } catch (e) {
      status(`Couldn't draw the label: ${e.message}`, true);
    } finally {
      rendering = false;
    }
  }

  const form = buildForm(options.form, options.defaults, (field) => {
    if (field.tab !== "output") refresh(); // copies and darkness don't change the picture
  });
  const spec = () => form.read();
  $("form").append(form.tabs);

  // the printer row belongs to the Output box but differs per client, so it isn't in the form description
  fill($("mode"), printer.modes);
  const saved = await store.get("printer", {});
  if (printer.modes.includes(saved.mode)) $("mode").value = saved.mode;
  $("address").value = saved.address || "";
  const syncPrinterRow = () => {
    $("address").hidden = $("mode").value !== "Bluetooth" || printer.modes.length < 2; // only the desktop has an address box
  };
  syncPrinterRow();
  $("printer-row").hidden = printer.modes.length < 2;
  const rememberPrinter = () => {
    syncPrinterRow();
    store.set("printer", { mode: $("mode").value, address: $("address").value.trim() });
  };
  $("mode").addEventListener("input", rememberPrinter);
  $("address").addEventListener("change", rememberPrinter);
  form.output.append($("printer-row"));
  $("output").append(form.output);

  function draw(gray) {
    last = gray;
    const image = context.createImageData(width, stickerHeight);
    for (let i = 0; i < width * stickerHeight; i++) {
      const v = gray[i];
      image.data.set([v, v, v, 255], i * 4);
    }
    context.putImageData(image, 0, 0);
  }

  async function print() {
    const current = spec();
    if (!current.text.trim() && !current.qr.trim()) return status("Nothing to print.");
    $("print").disabled = true;
    status("Printing…");
    const result = await printer.print(current, { mode: $("mode").value, address: $("address").value.trim() });
    $("print").disabled = false;
    if (result.error) status(result.error, true);
    else status(result.problems.length ? `Printer: ${result.problems.join(", ")}` : "Sent.");
  }
  $("print").addEventListener("click", print);
  $("print").disabled = false;
  status("");
  await refresh();
  // For tests and the desktop checks: the label as the page sees it, and whether it is idle.
  window.__t003 = { client: desktop ? "desktop" : "web", spec, form, refresh, idle: () => !rendering, pixels: () => last };
}

function fill(select, values) {
  for (const value of values) select.append(new Option(value, value));
}

main().catch((e) => status(e.message || String(e), true));
