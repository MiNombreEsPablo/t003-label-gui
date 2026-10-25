// Printer seam, browser adapter: print over Web Bluetooth (Chrome/Edge/Opera on Android and desktop; not Safari, iOS
// or Firefox). The UUIDs, chunk size and gap come from the engine's options (src/t003gui/bluetooth.py), so nothing about
// the printer is repeated here.
//   modes: string[]   print(spec, {mode, address}) -> {problems: string[], error: string|null}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function createPrinter(engine, options) {
  const { ble, name_prefix: namePrefix, status_query: statusQuery } = options.bluetooth;
  let device = null;
  let writeChar = null;
  let onStatus = null; // set while we wait for the printer's reply to a status query
  let busy = Promise.resolve(); // one print at a time: overlapping GATT writes fail

  const isConnected = () => device && device.gatt.connected && writeChar;

  async function connect() {
    if (!navigator.bluetooth) throw new Error("This browser has no Web Bluetooth. Use Chrome or Edge (Android or desktop).");
    if (!device) {
      device = await navigator.bluetooth.requestDevice({
        filters: [{ namePrefix }],
        optionalServices: [ble.service],
      });
    }
    const server = await device.gatt.connect();
    const service = await server.getPrimaryService(ble.service);
    writeChar = await service.getCharacteristic(ble.write);
    const notify = await service.getCharacteristic(ble.notify);
    notify.addEventListener("characteristicvaluechanged", (event) => {
      if (onStatus) onStatus(event.target.value.getUint8(0));
    });
    await notify.startNotifications();
  }

  async function write(bytes) {
    for (let i = 0; i < bytes.length; i += ble.chunk) {
      const part = bytes.slice(i, i + ble.chunk);
      if (writeChar.properties.writeWithoutResponse) await writeChar.writeValueWithoutResponse(part);
      else await writeChar.writeValueWithResponse(part);
      await sleep(ble.gap_ms);
    }
  }

  // The printer's status byte, or null when it doesn't answer (like core.send, that is not an error).
  async function status() {
    const reply = new Promise((resolve) => {
      onStatus = resolve;
      setTimeout(() => resolve(null), 1500);
    });
    await write(Uint8Array.from(statusQuery));
    const byte = await reply;
    onStatus = null;
    return byte;
  }

  async function printNow(spec) {
    if (!isConnected()) await connect(); // first, while the click still counts as a user gesture (the chooser needs it)
    await write(await engine.tspl(spec));
    await sleep(300);
    const byte = await status();
    return { problems: byte === null ? [] : await engine.statusProblems(byte), error: null };
  }

  return {
    modes: ["Bluetooth"],
    print(spec) {
      const run = busy.then(() => printNow(spec)).catch((e) => ({
        problems: [],
        error: e.name === "NotFoundError" ? "No printer chosen." : e.message || String(e),
      }));
      busy = run;
      return run;
    },
  };
}
