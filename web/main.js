// The UI, written once. It only ever talks to three seams, whichever client it runs in:
//   engine:  options(), preview(spec) -> {pixels, hints}                 (engine/pyodide.js or engine/bridge.js)
//   printer: modes, print(spec, {mode, address}) -> {problems, error}    (printer/ble.js or printer/bridge.js)
//   store:   get(key, fallback), set(key, value)                         (store/local.js or store/bridge.js)
//   files:   save(bytes, name, mime), copyImage(png)                     (files/browser.js or files/bridge.js)
// The desktop shell opens this page with ?client=desktop; anywhere else it is the browser build.
// The label's simple controls are built from the description the engine provides (form.js).

import { buildForm } from "./form.js";
import { createImageWidget } from "./image.js";
import { createDoodleWidget } from "./doodle.js";
import { applyTheme, DEFAULT_THEME, previewColors, THEMES } from "./themes.js";

const desktop = new URLSearchParams(location.search).get("client") === "desktop";
const $ = (id) => document.getElementById(id);
const status = (text, isError = false) => {
  $("status").textContent = text;
  $("status").classList.toggle("error", isError);
};

async function connectSeams() {
  if (desktop) {
    const [engineModule, printerModule, storeModule, filesModule] = await Promise.all([
      import("./engine/bridge.js"), import("./printer/bridge.js"), import("./store/bridge.js"), import("./files/bridge.js"),
    ]);
    const engine = engineModule.createEngine();
    await engine.init();
    return { engine, store: storeModule.createStore(), files: filesModule.createFiles(), makePrinter: () => printerModule.createPrinter() };
  }
  const [engineModule, printerModule, storeModule, filesModule] = await Promise.all([
    import("./engine/pyodide.js"), import("./printer/ble.js"), import("./store/local.js"), import("./files/browser.js"),
  ]);
  const engine = engineModule.createEngine(new URL("./", location.href).href);
  await engine.init(status);
  return { engine, store: storeModule.createStore(), files: filesModule.createFiles(), makePrinter: (options) => printerModule.createPrinter(engine, options) };
}

async function main() {
  status("Starting…");
  const { engine, store, files, makePrinter } = await connectSeams();
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
        // while drawing, the engine renders the label without its doodle: the overlay shows the ink, and the bucket
        // needs the label alone to know where the text is
        const { pixels, hints } = await engine.preview(activeTab === "doodle" ? { ...spec(), doodle: "" } : spec());
        draw(pixels);
        if (activeTab === "doodle") doodle.setUnderlay(pixels);
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

  // a picture the user chose, dropped or pasted: the engine takes it in and hands back the path the label uses
  async function useFile(file) {
    if (!file) return;
    status(`Reading ${file.name}…`);
    const started = performance.now();
    try {
      const path = await engine.addImage(new Uint8Array(await file.arrayBuffer()), file.name);
      picture.current().set(path, file.name);
      form.refreshState();
      status("");
      await refresh();
      const seconds = (performance.now() - started) / 1000;
      if (seconds > 1.5) status(`${file.name} (${(file.size / 1e6).toFixed(1)} MB) took ${seconds.toFixed(1)} s to load.`);
    } catch (e) {
      status(`Couldn't use that picture: ${e.message}`, true);
    }
  }
  const picture = createImageWidget(useFile, (text) => status(text, true));
  const doodle = createDoodleWidget(options);
  document.querySelector(".paper").append(doodle.overlay);
  let activeTab = "";
  const form = buildForm(options.form, options.defaults, (field) => {
    if (field.tab === "output") return; // copies and darkness don't change the picture
    if (field.name === "doodle" && activeTab === "doodle") return; // the overlay already shows what was drawn
    refresh();
  }, { image: picture.make, doodle: doodle.make }, (id) => {
    const wasDrawing = activeTab === "doodle";
    activeTab = id;
    doodle.setActive(id === "doodle");
    if (wasDrawing || id === "doodle") refresh(); // the doodle moves between the engine's picture and the overlay
  });

  const pictureIn = (transfer) => Array.from((transfer && transfer.files) || []).find((f) => f.type.startsWith("image/"));
  addEventListener("dragover", (event) => {
    if (Array.from(event.dataTransfer.items || []).some((i) => i.kind === "file")) {
      event.preventDefault();
      document.body.classList.add("dropping");
    }
  });
  addEventListener("dragleave", (event) => {
    if (!event.relatedTarget) document.body.classList.remove("dropping");
  });
  addEventListener("drop", (event) => {
    document.body.classList.remove("dropping");
    const label = Array.from((event.dataTransfer && event.dataTransfer.files) || []).find((f) => f.name.toLowerCase().endsWith(".t003label"));
    if (label) {
      event.preventDefault();
      openLabelFile(label);
      return;
    }
    const file = pictureIn(event.dataTransfer);
    if (file) {
      event.preventDefault();
      useFile(file);
    }
  });
  addEventListener("paste", (event) => { // a picture on the clipboard wins even in a text box; text pastes as usual
    const file = pictureIn(event.clipboardData);
    if (file) {
      event.preventDefault();
      useFile(file);
    }
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
    const { ink, paper } = previewColors(); // black on white, or the tint of the chosen look
    const image = context.createImageData(width, stickerHeight);
    for (let i = 0; i < width * stickerHeight; i++) {
      image.data.set(gray[i] < 128 ? ink : paper, i * 4);
      image.data[i * 4 + 3] = 255;
    }
    context.putImageData(image, 0, 0);
  }

  // the look: remembered, applied at once; the preview and the doodle ink follow its tint
  for (const [key, title] of THEMES) $("theme").append(new Option(title, key));
  const retint = () => {
    if (last) draw(last);
    doodle.setInk(previewColors().ink);
  };
  $("theme").value = applyTheme(await store.get("theme", DEFAULT_THEME));
  retint();
  $("theme").addEventListener("input", () => {
    applyTheme($("theme").value);
    store.set("theme", $("theme").value);
    retint();
  });

  const hasContent = (label) => options.content_fields.some((name) => String(label[name]).trim()); // as spec.has_content

  // saving and copying the label as an image: the engine renders the PNG, the files seam delivers it
  for (const [scale, name] of options.export.scales) $("export-size").append(new Option(name, scale));
  $("export-size").value = await store.get("exportScale", options.export.scales[0][0]);
  $("export-size").addEventListener("input", () => store.set("exportScale", Number($("export-size").value)));
  async function makeImage(doing) {
    const current = spec();
    if (!hasContent(current)) {
      status(`Nothing to ${doing}.`);
      return null;
    }
    return engine.exportPng(current, Number($("export-size").value));
  }
  $("save-image").addEventListener("click", async () => {
    try {
      const image = await makeImage("save");
      if (!image) return;
      const result = await files.save(image.data, image.name, "image/png", "PNG image");
      if (result.error) status(result.error, true);
      else if (!result.cancelled) status(`Saved ${result.saved}.`);
    } catch (e) {
      status(`Couldn't save the image: ${e.message}`, true);
    }
  });
  $("copy-image").addEventListener("click", async () => {
    try {
      const image = await makeImage("copy");
      if (!image) return;
      await files.copyImage(image.data);
      status("Copied the label to the clipboard.");
    } catch (e) {
      status(`Couldn't copy the image: ${e.message}`, true);
    }
  });

  // the whole label design as a .t003label file (the picture travels inside it), and back
  async function openLabelFile(file) {
    try {
      form.write(await engine.compositionLoads(await file.text()));
      status(`Opened ${file.name}.`);
      await refresh();
    } catch (e) {
      status(`Couldn't open ${file.name}: ${e.message}`, true);
    }
  }
  $("open-label").addEventListener("click", () => $("label-file").click());
  $("label-file").addEventListener("change", () => {
    const [file] = $("label-file").files;
    $("label-file").value = "";
    if (file) openLabelFile(file);
  });
  $("save-label").addEventListener("click", async () => {
    try {
      const file = await engine.compositionDumps(spec());
      const result = await files.save(file.data, file.name, options.composition.mime, "T003 label");
      if (result.error) status(result.error, true);
      else if (!result.cancelled) status(`Saved ${result.saved}.`);
    } catch (e) {
      status(`Couldn't save the label: ${e.message}`, true);
    }
  });

  async function print() {
    const current = spec();
    if (!hasContent(current)) return status("Nothing to print.");
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
