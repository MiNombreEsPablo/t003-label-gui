// The UI, written once. It only ever talks to two seams, whichever client it runs in:
//   engine:  options(), preview(spec) -> W*H gray bytes          (engine/pyodide.js or engine/bridge.js)
//   printer: modes, print(spec, {mode, address}) -> {problems, error}  (printer/ble.js or printer/bridge.js)
// The desktop shell opens this page with ?client=desktop; anywhere else it is the browser build.

const desktop = new URLSearchParams(location.search).get("client") === "desktop";
const $ = (id) => document.getElementById(id);
const status = (text, isError = false) => {
  $("status").textContent = text;
  $("status").classList.toggle("error", isError);
};

async function connectSeams() {
  if (desktop) {
    const [{ createEngine }, { createPrinter }] = await Promise.all([import("./engine/bridge.js"), import("./printer/bridge.js")]);
    const engine = createEngine();
    await engine.init();
    return { engine, makePrinter: () => createPrinter() };
  }
  const [{ createEngine }, { createPrinter }] = await Promise.all([import("./engine/pyodide.js"), import("./printer/ble.js")]);
  const engine = createEngine(new URL("./", location.href).href);
  await engine.init(status);
  return { engine, makePrinter: (options) => createPrinter(engine, options) };
}

function fill(select, values, selected) {
  for (const value of values) select.append(new Option(value, value, false, value === selected));
}

async function main() {
  status("Starting…");
  const { engine, makePrinter } = await connectSeams();
  const options = await engine.options();
  const printer = makePrinter(options);
  const { width, height, sticker_height: stickerHeight } = options.geometry;

  fill($("font"), options.fonts.map((f) => f.family), options.default_font);
  fill($("effect"), options.effects, "none");
  fill($("mode"), printer.modes, printer.modes[0]);
  $("printer-row").hidden = printer.modes.length < 2;

  const canvas = $("preview");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");

  const spec = () => ({
    text: $("text").value,
    font: $("font").value,
    bold: $("bold").checked,
    effect: $("effect").value,
    border: $("border").checked,
  });

  let last = null;
  function draw(gray) {
    last = gray;
    const image = context.createImageData(width, height);
    for (let i = 0; i < gray.length; i++) {
      const v = gray[i];
      image.data.set([v, v, v, 255], i * 4);
    }
    context.putImageData(image, 0, 0);
    context.fillStyle = "rgba(0, 0, 0, 0.08)"; // the gap between stickers is never printed
    context.fillRect(0, stickerHeight, width, height - stickerHeight);
  }

  // Render the newest request only: while one is running, later keystrokes just replace the waiting one.
  let rendering = false;
  let again = false;
  async function refresh() {
    if (rendering) {
      again = true;
      return;
    }
    rendering = true;
    try {
      do {
        again = false;
        draw(await engine.preview(spec()));
      } while (again);
      if ($("status").classList.contains("error")) status("");
    } catch (e) {
      status(`Couldn't draw the label: ${e.message}`, true);
    } finally {
      rendering = false;
    }
  }

  async function print() {
    const current = spec();
    if (!current.text.trim()) return status("Nothing to print.");
    $("print").disabled = true;
    status("Printing…");
    const result = await printer.print(current, { mode: $("mode").value, address: $("address").value.trim() });
    $("print").disabled = false;
    if (result.error) status(result.error, true);
    else status(result.problems.length ? `Printer: ${result.problems.join(", ")}` : "Sent.");
  }

  for (const id of ["text", "font", "bold", "effect", "border"]) $(id).addEventListener("input", refresh);
  $("mode").addEventListener("input", () => ($("address").hidden = $("mode").value !== "Bluetooth"));
  $("print").addEventListener("click", print);
  $("print").disabled = false;
  $("address").hidden = true;
  status("");
  await refresh();
  // For tests and the desktop checks: what the page last drew, and whether it is idle.
  window.__t003 = { client: desktop ? "desktop" : "web", spec, refresh, idle: () => !rendering, pixels: () => last };
}

main().catch((e) => status(e.message || String(e), true));
